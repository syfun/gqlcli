import pyclip
from prompt_toolkit.application import Application
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Float, FloatContainer, HSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import TextArea

from .print import print_query

help_text = """
Type any mutation or query field to generate a query.
Press Control-C to exit.
"""


def make_app(schema):
    fields = list(schema.query_type.fields.keys()) + list(schema.mutation_type.fields.keys())
    completer = WordCompleter(fields)

    output_field = TextArea(style="class:output-field", text=help_text)
    input_field = TextArea(
        prompt=">>> ",
        style="class:input-field",
        multiline=False,
        wrap_lines=False,
        completer=completer,
        complete_while_typing=True,
    )

    body = FloatContainer(
        content=HSplit(
            [
                input_field,
                Window(height=1, char="-", style="class:line"),
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
        output = print_query(schema, input_field.text)

        pyclip.copy(output)

        new_text = output_field.text + "\n" + output

        # Add text to output buffer.
        output_field.buffer.document = Document(text=new_text, cursor_position=len(new_text))

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
