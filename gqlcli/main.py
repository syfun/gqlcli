from functools import partial
from pathlib import Path
from typing import cast

import click
import pyclip
import requests
from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
    assert_interface_type,
    assert_object_type,
)
from graphql import build_schema as _build_schema
from graphql import is_enum_type, is_input_object_type, is_interface_type, is_object_type, print_type
from graphql.utilities import build_client_schema, get_introspection_query

from .generator import FieldGenerator, TypeGenerator, TypeResolverGenerator
from .interactive import make_app
from .make_schema import make_schema_from_path
from .print import print_query

build_schema = partial(_build_schema, assume_valid_sdl=True)


def build_client_schema_with_host(host: str) -> GraphQLSchema:
    query = get_introspection_query()
    data = {"query": query}
    resp = requests.post(host, json=data)
    if not resp.ok:
        raise RuntimeError(f"get_introspection_query error: {resp.text}")
    data = resp.json()["data"]
    return build_client_schema(resp.json()["data"])


@click.group()
@click.option(
    "-p",
    "--path",
    help="graphql sdl path, support directory and file."
    "schema extension must be .graphql."
    'if not present, auto find "schema" directory and "schema.graphql"',
)
@click.option("-h", "--host", help="graphql server host ")
@click.pass_context
def main(ctx, path, host):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    if host:
        ctx.obj["schema"] = build_client_schema_with_host(host)
        return

    current_dir = Path(".")

    if not path:
        directory = current_dir / "schema"
        file = Path(".") / "schema.graphql"
    else:
        directory = current_dir / path
        file = current_dir / f"{path}"

    if file.exists() and file.is_file():
        ctx.obj["schema"] = make_schema_from_path(file, assume_valid=True)
        return

    if directory.exists() and directory.is_dir():
        ctx.obj["schema"] = make_schema_from_path(directory, assume_valid=True)
        return

    print("Must has 'path' argument or has a graphql sdl file schema.graphql " "or has a schema directory")


@main.command(name="t")
@click.pass_context
@click.option(
    "--kind",
    default="pydantic",
    help="generate class based: none, dataclass, pydantic, default is pydantic",
)
@click.option("--optional", default=False, is_flag=True, help="all field optional")
@click.option("--enum", default="str", help="enum type: str, number, default is str")
@click.argument("typ", nargs=-1)
def type(ctx, typ: str, kind: str, optional: bool, enum: str):
    """Generate one type"""
    generator = TypeGenerator(kind, optional=optional)
    type_map = ctx.obj["schema"].type_map
    for t in typ:
        if t not in type_map:
            print(f"No '{t}' type.")
            return

        type_ = type_map[t]
        type_def = ""
        if is_enum_type(type_):
            if enum == "str":
                type_def = generator.str_enum_type(cast(GraphQLEnumType, type_))
            elif enum == "number":
                type_def = generator.number_enum_type(cast(GraphQLEnumType, type_))
        elif is_object_type(type_):
            type_def = generator.object_type(cast(GraphQLObjectType, type_))
        elif is_interface_type(type_):
            type_def = generator.interface_type(cast(GraphQLInterfaceType, type_))
        elif is_input_object_type(type_):
            type_def = generator.input_type(cast(GraphQLInputObjectType, type_))

        print(type_def)


@main.command()
@click.pass_context
@click.option(
    "--kind",
    default="pydantic",
    help="generate class based: none, dataclass, pydantic, default is pydantic",
)
def all(ctx, kind: str):
    """Generate all schema types"""
    if kind not in ["none", "dataclass", "pydantic"]:
        print("KIND must be none, dataclass or pydantic")
        return

    generator = TypeGenerator(kind)

    enum_types, interface_types, object_types, input_types = [], [], [], []
    type_map = ctx.obj["schema"].type_map
    for name, type_ in type_map.items():
        if name in ["Query", "Mutation"] or name.startswith("__"):
            continue
        elif is_enum_type(type_):
            enum_types.append(generator.str_enum_type(cast(GraphQLEnumType, type_)))
        elif is_object_type(type_):
            object_types.append(generator.object_type(cast(GraphQLObjectType, type_)))
        elif is_interface_type(type_):
            interface_types.append(generator.interface_type(cast(GraphQLInterfaceType, type_)))
        elif is_input_object_type(type_):
            input_types.append(generator.input_type(cast(GraphQLInputObjectType, type_)))

    type_resolvers = TypeResolverGenerator(type_map).all_type_resolvers()
    imports, body = "", ""

    if enum_types:
        body += "\n".join(enum_types) + "\n"
    if interface_types:
        body += "\n".join(interface_types) + "\n"
    if object_types:
        body += "\n".join(object_types) + "\n"
    if input_types:
        body += "\n".join(input_types)
    if type_resolvers:
        body += "\n".join(type_resolvers)

    if kind == "dataclass":
        imports += "from dataclasses import dataclass\n"
    if enum_types:
        imports += "from enum import Enum\n"
    imports += "from typing import Any, Dict, List, NewType, Optional, Union\n\n"
    imports += "from gql import enum_type, type_resolver\n"
    if kind == "pydantic":
        imports += "from pydantic import BaseModel\n"
    imports += "\n"

    print(imports + body)


@main.command(name="fr")
@click.pass_context
@click.argument("type")
@click.argument("field")
def field_resolver(ctx, type: str, field: str):
    """Generate field resolver."""
    schema = ctx.obj["schema"]
    type_ = schema.get_type(type)
    if is_object_type(type_):
        type_ = assert_object_type(type_)
    elif is_interface_type(type_):
        type_ = assert_interface_type(type_)
    else:
        print(f"{type} is not type or not object type or not interface type")
        return

    field_ = type_.fields.get(field)
    if not field:
        print(f"{type} has no {field} field")
        return

    if type == "Query":
        output = "@query\ndef "
    elif type == "Mutation":
        output = "@mutate\ndef "
    elif type == "Subscription":
        output = "@subscribe\ndef "
    else:
        output = f"@field_resolver('{type}', '{field}')\ndef "
    output += FieldGenerator.resolver_field(field, field_) + ":\n    pass\n"
    print(output)


@main.command(name="tr")
@click.pass_context
@click.argument("type_name")
def type_resolver(ctx, type_name: str):
    """Generate type resolver"""
    generator = TypeResolverGenerator(ctx.obj["schema"].type_map)
    print(generator.type_resolver(type_name))


@main.command(name="c")
@click.pass_context
@click.argument("op")
def client(ctx, op: str):
    """Generate client query"""
    schema: GraphQLSchema = ctx.obj["schema"]
    result = print_query(schema, op)
    print(result)
    pyclip.copy(result)


@main.command(name="i")
@click.pass_context
def interactive(ctx):
    """Interactive mode."""
    schema: GraphQLSchema = ctx.obj["schema"]

    app = make_app(schema)
    app.run()


@main.command(name="pt")
@click.pass_context
@click.argument("type_name")
def print_graphql_type(ctx, type_name: str):
    """Print type definition"""
    schema = ctx.obj["schema"]
    type_ = schema.get_type(type_name)
    if not type_:
        print(f"No {type_name} type.")
        return
    print(print_type(type_))
