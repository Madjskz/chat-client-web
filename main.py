import asyncio
import json

import websockets

from textual import work, on
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Container, Horizontal
from textual.screen import Screen
from textual.widgets import Header, Static, Label, Input, Button, Footer


URI: str = "ws://localhost:8765"


class Authorization_screen(Screen):
    def compose(self) -> ComposeResult:
        yield Container(
            Label('Authorization', id='auth_label'),
            Input(id='login', placeholder='Login', classes='auth_input'),
            Input(id='password', placeholder='Password', classes='auth_input'),
            Button(id='auth_button', label='Send'),
            id='dialog_auth')


class Chat_screen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        user_container = ScrollableContainer(id='user_container')
        user_container.styles.width = 20
        user_container.styles.scrollbar_size_vertical = 1
        user_container.styles.scrollbar_color = "#737373"
        user_container.styles.scrollbar_color_active = "#817D74"
        user_container.styles.scrollbar_color_hover = "#817D74"

        message_container = ScrollableContainer(id='message_container')
        message_container.styles.scrollbar_size_vertical = 1
        message_container.styles.scrollbar_color = "#737373"
        message_container.styles.scrollbar_color_active = "#817D74"
        message_container.styles.scrollbar_color_hover = "#817D74"

        yield Container(
            Horizontal(
                user_container,
                message_container
            )
        )

        yield Input(id='input_message', placeholder='Введите сообщение')
        yield Footer()


class ChatApp(App):
    CSS_PATH = 'main.tcss'

    ENABLE_COMMAND_PALETTE = False

    MODES = {
        'authorization': Authorization_screen,
        'chat': Chat_screen
    }

    BINDINGS = [
        ('d', 'toggle_dark', 'Toggle dark mode'),
    ]

    def on_mount(self) -> None:
        self.switch_mode('authorization')
        self.title = "MAGNET1C H1LLS CHAT"
        self.dark = not self.dark

    def __init__(self):
        super().__init__()

        self.current_user_id: int = 0

        self.message_wait_send: list = []
        self.users_list: list = []
        self.messages_list: list = []

        self.messages_wait_add: list = []
        self.users_wait_add: list = []

    is_load_init_data: bool = False

    @on(Button.Pressed, '#auth_button')
    async def on_button_pressed(self) -> None:
        self.websocket_start(
            self.query_one('#login').value,
            self.query_one('#password').value
        )

    @work
    async def websocket_start(self, login, password) -> None:
        async with websockets.connect(URI) as self.websocket:
            await self.websocket.send(json.dumps({
                'username': login,
                'password': password
            }))

            self.current_user_id = int(str(await self.websocket.recv()).split()[0])

            await self.switch_mode('chat')

            await asyncio.gather(self.listen_server(self.websocket))

    @work
    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == 'input_message':
            if self.query_one(Input).value:
                await self.send_message_on_server(self.query_one(Input).value)

            self.query_one(Input).value = ''

    async def listen_server(self, websocket: websockets) -> None:
        try:
            while True:
                if (self._exit or self.return_value or self.return_code
                        or (not self.is_running) or self.is_headless):
                    await websocket.close()

                try:
                    recv = await asyncio.wait_for(websocket.recv(), timeout=1)
                    type_recv = recv[0] if len(recv) else None

                    match type_recv:
                        case '0':
                            await self.get_new_message(json.loads(recv[1:]))
                        case '1':
                            await self.get_online_status(json.loads(recv[1:]))
                        case '2':
                            await self.get_new_user(json.loads(recv[1:]))
                        case '3':
                            await self.delete_message(json.loads(recv[1:]))
                        case 'R':
                            ChatApp.is_load_init_data = True
                            await self.add_init_data()
                except asyncio.TimeoutError:
                    ...
        finally:
            ...

    async def get_new_message(self, js: json) -> None:
        self.messages_list.append(Message(js['ID'], await self.find_username(js['OwnerID']),
                                          js['Message'], js['Date']))

        if ChatApp.is_load_init_data:
            await self.query_one("#message_container").mount(self.messages_list[-1])
            self.messages_list[-1].scroll_visible(duration=None, speed=None, animate=False)

    async def find_username(self, id: int) -> str:
        for user in self.users_list:
            if user.id_user == id:
                return user.username

    async def get_online_status(self, js: json) -> None:
        for i in range(len(self.users_list)):
            if self.users_list[i].id_user == js['ID']:
                self.users_list[i].change_online_status(js['OnlineStatus'])

    async def get_new_user(self, js: json) -> None:
        self.users_list.append(User(js['ID'], js['Name'], js['OnlineStatus']))

        if ChatApp.is_load_init_data:
            await self.query_one("#user_container").mount(self.users_list[-1])

    async def delete_message(self, js: json) -> None:
        self.query_one(f'#user_field_{js["idMessage"]}').parent.remove()

    async def add_init_data(self):
        await asyncio.gather(
            self.query_one("#message_container").mount(*self.messages_list),
            self.query_one("#user_container").mount(*self.users_list)
        )
        self.messages_list[-1].scroll_visible(duration=None, speed=None, animate=False)

    async def send_message_on_server(self, message: str) -> None:
        await self.websocket.send(json.dumps({
            'OwnerID': self.current_user_id,
            'Message': message
        }))

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark


class Message(Static):
    def __init__(self, id_message: int = -1, username: str = 'user', text: str = 'text', date: str = 'date'):
        super().__init__()
        self.id_message = id_message
        self.username = username
        self.text = text
        self.date = date

    def compose(self):
        yield Static(self.username, id=f'user_field_{self.id_message}')
        yield Static(self.text, id=f'message_field_{self.id_message}')
        yield Static(self.date, id=f'date_field_{self.id_message}')


class User(Static):
    def __init__(self, id_user: int = -1, username: str = 'user', online_status: bool = False):
        super().__init__()
        self.id_user = id_user
        self.username = username
        self.online_status = online_status

        self.static = None

    def compose(self):
        self.static = Static(self.username, id=f'user_online_field_{self.id_user}')
        self.static.styles.color = 'green' if self.online_status else 'red'

        yield self.static

    def change_online_status(self, online_status):
        self.online_status = online_status
        if ChatApp.is_load_init_data:
            self.query_one(f'#user_online_field_{self.id_user}').styles.color = 'green' if self.online_status else 'red'


if __name__ == "__main__":
    app = ChatApp()
    app.run()
