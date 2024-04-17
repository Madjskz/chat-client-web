import asyncio

import websockets

from textual import work, events
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static, Label, Input


class Message(Static):
    def compose(self):
        yield Label('user', id='user_field')
        yield Label('message', id='message_field')
        yield Label('date', id='date_field')


class User(Static):
    def compose(self) -> None:
        yield Label('user')


class User(Static):
    def compose(self):
        yield Label('user', id='user_online_field')


class ChatApp(App):
    """A Textual app to manage stopwatches."""

    DEFAULT_CSS = """
    Message {
        margin: 1;
        border: solid red;
        text-style: italic;
    }

    #message {
        background: $boost;
    }

    #input {
        background: grey;
    }

    #user_field {
        text-style: underline;
    }

    #message_field {

    }

    #date_field {
        text-style: bold;
    }
    """

    BINDINGS = [
        ("ctrl+a", "add_message", "Add"),
        ("ctrl+r", "remove_message", "Remove"),
    ]

    async def on_load(self):
        self.listen_server()

    @work(exclusive=True)
    async def listen_server(self):
        while True:
            self.query_one(Input).value += "1"
            await asyncio.sleep(2)

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Header(name='MAGNET1C H1LLS CHAT')
        yield Footer()

        user_container = ScrollableContainer(id='user_container')
        user_container.styles.width = 20
        yield Container(
            Horizontal(
                user_container,
                ScrollableContainer(id='message_container')
            )
        )

        yield Input(id='input', placeholder='Введите сообщение')

    def action_add_message(self) -> None:
        """An action to add a timer."""
        self.query_one("#message_container").mount(Message())
        self.query_one("#user_container").mount(User())

    def action_remove_message(self) -> None:
        """Called to remove a timer."""
        message = self.query("Message")
        if message:
            message.last().remove()

    def key_enter(self, event: events.Key):
        self.query_one(Input).value = ''


if __name__ == "__main__":
    app = ChatApp()
    app.run()
