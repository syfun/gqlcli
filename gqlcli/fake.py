import json
import random
import time
from typing import Any

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLInputType,
    GraphQLScalarType,
    GraphQLWrappingType,
    assert_enum_type,
    assert_input_object_type,
    assert_scalar_type,
    is_enum_type,
    is_input_object_type,
    is_scalar_type,
)


def fake_variable(field: GraphQLField) -> str:
    variable = {}

    for arg_name, arg in field.args.items():
        variable[arg_name] = fake_input_type(arg.type)

    return json.dumps(variable, indent=2, ensure_ascii=False)


def fake_input_type(type_: GraphQLInputType) -> Any:
    if isinstance(type_, GraphQLWrappingType):
        type_ = type_.of_type

    if is_scalar_type(type_):
        return fake_scalar_type(assert_scalar_type(type_))
    elif is_enum_type(type_):
        return fake_enum_type(assert_enum_type(type_))
    elif is_input_object_type(type_):
        return fake_input_object_type(assert_input_object_type(type_))
    else:
        return ""


def fake_scalar_type(type_: GraphQLScalarType) -> Any:

    if type_.name == "String":
        return "string"
    elif type_.name == "Boolean":
        return True
    elif type_.name == "Int":
        return 10
    elif type_.name == "Float":
        return 1.1
    elif type_.name == "Timestamp":
        return int(time.time() * 1000)
    elif type_.name == "JSON":
        return {}
    else:
        return ""


def fake_enum_type(type_: GraphQLEnumType) -> Any:
    return random.choice(list(type_.values.values()))


def fake_input_object_type(type_: GraphQLInputObjectType) -> Any:
    return {field_name: fake_input_type(field.type) for field_name, field in type_.fields.items()}
