from typing import List, Tuple

from graphql import GraphQLObjectType, GraphQLOutputType, is_object_type, is_scalar_type


def print_args(args) -> Tuple[list, list]:
    var_defs, vars = [], []
    for name, argument in args.items():
        var_defs.append(f"${name}: {argument.type}")
        vars.append(f"{name}: ${name}")
    return var_defs, vars


def of_type(type_: GraphQLOutputType) -> GraphQLOutputType:
    try:
        t = type_.of_type
    except AttributeError:
        return type_
    else:
        return of_type(t)


def print_block(items: List[str], indent=0) -> str:
    return " {\n" + "\n".join(items) + "\n" + " " * indent + "}" if items else ""


def print_field(type_: GraphQLObjectType, indent: int = 2, type_set: set = None) -> str:
    if is_scalar_type(type_):
        return ""
    items = []
    indent_space = " " * indent
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
    fields = "  " + op + print_field(return_type, indent=4)
    return op_type + " " + operation_name + print_block([fields])


def print_query(schema, op: str):
    query = schema.query_type.fields.get(op)
    op_type = "query"
    if not query:
        query = schema.mutation_type.fields.get(op)
        op_type = "mutation"
        if not query:
            return f"No {op} query."

    return build_client(query, op, op_type)
