import pyclip
from graphql import GraphQLSchema, print_type
from prompt_toolkit.application import Application
from prompt_toolkit.completion import NestedCompleter, WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import HorizontalLine, TextArea

from .fake import fake_variable
from .print import print_query

help_text = """
Type any mutation or query field to generate a query.
Or type name to show.
Press Control-C to exit.
"""


def make_app(schema: GraphQLSchema):
    fields_completer = WordCompleter(list(schema.query_type.fields.keys()) + list(schema.mutation_type.fields.keys()))
    completer = NestedCompleter.from_nested_dict(
        {
            "client": fields_completer,
            "fakeVariable": fields_completer,
            "type": WordCompleter(list(schema.type_map.keys())),
            "exit": None,
        }
    )

    output_field = TextArea(style="class:output-field", text=help_text)
    input_field = TextArea(
        prompt=">>> ",
        # style="class:input-field",
        multiline=False,
        # wrap_lines=False,
        completer=completer,
        complete_while_typing=True,
    )

    body = FloatContainer(
        content=HSplit(
            [
                input_field,
                HorizontalLine(),
                output_field,
            ]
        ),
        floats=[
            Float(
                xcursor=True,
                ycursor=True,
                content=CompletionsMenu(max_height=16, scroll_offset=1),
            )
        ],
    )

    # Attach accept handler to the input field. We do this by assigning the
    # handler to the `TextArea` that we created earlier. it is also possible to
    # pass it to the constructor of `TextArea`.
    # NOTE: It's better to assign an `accept_handler`, rather then adding a
    #       custom ENTER key binding. This will automatically reset the input
    #       field and add the strings to the history.
    def accept(buff):
        command, value = input_field.text.split(" ")

        if command == "client":
            output = print_query(schema, value)
        elif command == "fakeVariable":
            field = schema.query_type.fields.get(value)
            if not field:
                field = schema.mutation_type.fields.get(value)
            output = fake_variable(field)
        elif command == "type":
            output = print_type(schema.type_map[value])
        else:
            output = input_field.text

        pyclip.copy(output)

        new_output_text = output_field.text + "\n" + output
        new_input_text = input_field.text + "\n" + ">>> "

        # Add text to output buffer.
        output_field.buffer.document = Document(text=new_output_text, cursor_position=len(new_output_text))
        input_field.buffer.document = Document(text=new_input_text, cursor_position=len(new_input_text))

    input_field.accept_handler = accept

    # The key bindings.
    kb = KeyBindings()

    @kb.add("c-c")
    @kb.add("c-q")
    def _(event):
        "Pressing Ctrl-Q or Ctrl-C will exit the user interface."
        event.app.exit()

    # # Style.
    # style = Style(
    #     [
    #         ("output-field", "bg:#0b120d #fffeee"),
    #         ("input-field", "bg:#000000 #ffffff"),
    #         ("line", "#004400"),
    #     ]
    # )

    # Run application.
    application = Application(
        layout=Layout(body),
        key_bindings=kb,
        # style=style,
        # mouse_support=True,
        full_screen=True,
    )

    return application
