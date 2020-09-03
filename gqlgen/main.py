import os
import json
from typing import List, Text, Tuple, cast
from functools import partial

import click
from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLOutputType,
    assert_interface_type,
    assert_object_type,
    build_schema as _build_schema,
    is_enum_type,
    is_input_object_type,
    is_interface_type,
    is_object_type,
    is_scalar_type,
    print_type,
)

from .generator import FieldGenerator, TypeGenerator, TypeResolverGenerator
from .utils import make_postman_request, make_headers

build_schema = partial(_build_schema, assume_valid_sdl=True)


@click.group()
@click.option('-f', '--file', help='graphql sdl file, file extension may be .gql or .graphql')
@click.pass_context
def main(ctx, file):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    if not file:
        file = guess_schema_file()
    if not file:
        print("Must has 'file' argument or has a graphql sdl file which endswith .gql or .graphql.")
        return
    with open(file, 'r') as f:
        ctx.obj['type_defs'] = f.read()


def guess_schema_file():
    files = os.listdir(os.path.curdir)
    for f in files:
        if os.path.isdir(f):
            continue
        if f.endswith('.gql') or f.endswith('.graphql'):
            return f
    return None


@main.command(name='t')
@click.pass_context
@click.option(
    '--kind',
    default='pydantic',
    help='generate class based: none, dataclass, pydantic, default is pydantic',
)
@click.option('--optional', default=False, is_flag=True, help='all field optional')
@click.option('--enum', default='str', help='enum type: str, number, default is str')
@click.argument('typ', nargs=-1)
def type(ctx, typ: str, kind: str, optional: bool, enum: str):
    """Generate one type"""
    generator = TypeGenerator(kind, optional=optional)
    type_map = build_schema(ctx.obj['type_defs']).type_map
    for t in typ:
        if t not in type_map:
            print(f"No '{t}' type.")
            return

        type_ = type_map[t]
        type_def = ''
        if is_enum_type(type_):
            if enum == 'str':
                type_def = generator.str_enum_type(cast(GraphQLEnumType, type_))
            elif enum == 'number':
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
    '--kind',
    default='pydantic',
    help='generate class based: none, dataclass, pydantic, default is pydantic',
)
def all(ctx, kind: str):
    """Generate all schema types"""
    if kind not in ['none', 'dataclass', 'pydantic']:
        print('KIND must be none, dataclass or pydantic')
        return

    generator = TypeGenerator(kind)

    enum_types, interface_types, object_types, input_types = [], [], [], []
    type_map = build_schema(ctx.obj['type_defs']).type_map
    for name, type_ in type_map.items():
        if name in ['Query', 'Mutation'] or name.startswith('__'):
            continue
        elif is_enum_type(type_):
            enum_types.append(generator.enum_type(cast(GraphQLEnumType, type_)))
        elif is_object_type(type_):
            object_types.append(generator.object_type(cast(GraphQLObjectType, type_)))
        elif is_interface_type(type_):
            interface_types.append(generator.interface_type(cast(GraphQLInterfaceType, type_)))
        elif is_input_object_type(type_):
            input_types.append(generator.input_type(cast(GraphQLInputObjectType, type_)))

    type_resolvers = TypeResolverGenerator(type_map).all_type_resolvers()
    imports, body = '', ''

    body += "ID = NewType('ID', Text)\n\n"
    if enum_types:
        body += '\n'.join(enum_types) + '\n'
    if interface_types:
        body += '\n'.join(interface_types) + '\n'
    if object_types:
        body += '\n'.join(object_types) + '\n'
    if input_types:
        body += '\n'.join(input_types)
    if type_resolvers:
        body += '\n'.join(type_resolvers)

    if kind == 'dataclass':
        imports += 'from dataclasses import dataclass\n'
    if enum_types:
        imports += 'from enum import Enum\n'
    imports += 'from typing import Any, Dict, List, NewType, Optional, Text, Union\n\n'
    imports += 'from gql import enum_type, type_resolver\n'
    if kind == 'pydantic':
        imports += 'from pydantic import BaseModel\n'
    imports += '\n'

    print(imports + body)


@main.command(name='fr')
@click.pass_context
@click.argument('type')
@click.argument('field')
def field_resolver(ctx, type: str, field: str):
    """Generate field resolver."""
    schema = build_schema(ctx.obj['type_defs'])
    type_ = schema.get_type(type)
    if is_object_type(type_):
        type_ = assert_object_type(type_)
    elif is_interface_type(type_):
        type_ = assert_interface_type(type_)
    else:
        print(f'{type} is not type or not object type or not interface type')
        return

    field_ = type_.fields.get(field)
    if not field:
        print(f'{type} has no {field} field')
        return

    if type == 'Query':
        output = f'@query\ndef '
    elif type == 'Mutation':
        output = f'@mutate\ndef '
    elif type == 'Subscription':
        output = f'@subscribe\ndef '
    else:
        output = f"@field_resolver('{type}', '{field}')\ndef "
    output += FieldGenerator.resolver_field(field, field_) + ':\n    pass\n'
    print(output)


@main.command(name='tr')
@click.pass_context
@click.argument('type_name')
def type_resolver(ctx, type_name: str):
    """Generate type resolver"""
    generator = TypeResolverGenerator(build_schema(ctx.obj['type_defs']).type_map)
    print(generator.type_resolver(type_name))


def print_args(args) -> Tuple[list, list]:
    var_defs, vars = [], []
    for name, argument in args.items():
        var_defs.append(f'${name}: {argument.type}')
        vars.append(f'{name}: ${name}')
    return var_defs, vars


def of_type(type_: GraphQLOutputType) -> GraphQLOutputType:
    try:
        t = type_.of_type
    except AttributeError:
        return type_
    else:
        return of_type(t)


def print_block(items: List[Text], indent=0) -> Text:
    return ' {\n' + '\n'.join(items) + '\n' + ' ' * indent + '}' if items else ''


def print_field(type_: GraphQLObjectType, indent: int = 2, type_set: set = None) -> str:
    if is_scalar_type(type_):
        return ''
    items = []
    indent_space = ' ' * indent
    type_set = type_set or set()
    for name, field in type_.fields.items():
        item = indent_space + name
        t = of_type(field.type)
        if t.name not in type_set:
            type_set.add(t.name)
            if is_object_type(t):
                item += print_field(t, indent + 2, type_set)
        # elif is_interface_type(t):
        #     if not inner_type:
        #         raise RuntimeError(f'{t} is a interface type, must have inner type.')
        #     item_ = f'{" " * (indent+2)}... on {inner_type.name}{print_field(inner_type, indent+4)}'
        #     item += print_block([item_], indent)
        items.append(item)
    return print_block(items, indent - 2)


def build_client(query, op, op_type):
    operation_name = op
    if query.args:
        var_defs, vars = print_args(query.args)
        operation_name += f'({", ".join(var_defs)})'
        op += f'({", ".join(vars)})'
    return_type = of_type(query.type)
    fields = '  ' + op + print_field(return_type, indent=4)
    return op_type + ' ' + operation_name + print_block([fields])


@main.command(name='c')
@click.pass_context
@click.argument('op')
@click.option('--type', '-T', default='normal')
def client(ctx, op: str, type: str = 'normal'):
    """Generate client query"""
    schema = build_schema(ctx.obj['type_defs'])
    query = schema.query_type.fields.get(op)
    op_type = 'query'
    if not query:
        query = schema.mutation_type.fields.get(op)
        op_type = 'mutation'
        if not query:
            print(f'No {op} query.')
            return

    r = build_client(query, op, op_type)
    if type == 'sf':
        r = {'operationName': op, 'variables': {'file': None}, 'query': str(r)}
        print("use form data")
        print(f"operations: {json.dumps(r)}")
        print("""map: {"1":["variables.file"]}""")
    elif type == 'mf':
        r = {'operationName': op, 'variables': {'files': [None]}, 'query': str(r)}
        print("use form data")
        print(f"operations: {json.dumps(r)}")
        print("""map: {"1":["variables.files.0"]}""")
    else:
        print(r)


@main.command(name='pt')
@click.pass_context
@click.argument('type_name')
def print_graphql_type(ctx, type_name: str):
    """Print type definition"""
    schema = build_schema(ctx.obj['type_defs'])
    type_ = schema.get_type(type_name)
    if not type_:
        print(f'No {type_name} type.')
        return
    print(print_type(type_))


@main.command(name='postman')
@click.argument('name')
@click.option('--header', '-H', multiple=True)
@click.pass_context
def export_postman(ctx, name: str, header):
    """Export all client query to postman."""
    schema = build_schema(ctx.obj['type_defs'])
    headers = make_headers(header)
    requests = []
    query_type, mutation_type = schema.query_type, schema.mutation_type
    if query_type:
        for op, field in query_type.fields.items():
            requests.append(make_postman_request(op, build_client(field, op, 'query'), headers))
    if mutation_type:
        for op, field in mutation_type.fields.items():
            requests.append(make_postman_request(op, build_client(field, op, 'mutation'), headers))

    data = {
        'info': {
            'name': name,
            'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
        },
        'item': requests,
        'protocolProfileBehavior': {},
    }
    with open(f'{name}.json', 'w') as f:
        json.dump(data, f, indent=2)
