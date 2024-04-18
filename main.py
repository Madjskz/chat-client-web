import asyncio
import json

import websockets

from textual import work, events
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Container, Horizontal
from textual.widgets import Footer, Header, Static, Label, Input

URI: str = "ws://localhost:8765"

app_is_closing: bool = False

users_list: list = []
messages_list: list = []

current_user_id = 1

waiting_message = []


class Message(Static):
    def __init__(self, id: int = -1, username: str = 'user', text: str = 'text', date: str = 'date'):
        super().__init__()
        self.id_message = id
        self.username = username
        self.text = text
        self.date = date

    def compose(self):
        yield Label(self.username, id=f'user_field')
        yield Label(self.text, id='message_field')
        yield Label(self.date, id='date_field')


class User(Static):
    def __init__(self, id_user: int = -1, username: str = 'user', online_status: bool = False):
        super().__init__()
        self.id_user = id_user
        self.username = username
        self.online_status = online_status

        self.label = None

    def compose(self):
        self.label = Label(self.username, id=f'user_online_field')
        self.label.styles.visibility = 'visible' if self.online_status else 'hidden'

        yield self.label

    def change_online_status(self, online_status):
        self.online_status = online_status
        self.label.styles.visibility = 'visible' if online_status else 'hidden'


class ChatApp(App):
    DEFAULT_CSS = """
    Message {
        margin: 1;
        border: solid red;
        text-style: italic;
    }
    
    User {
        margin: 1
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
        ("q", "close", "Close"),
    ]

    def __init__(self):
        super().__init__()
        self.is_close = False
        self.message_wait_send = []

    async def on_load(self) -> None:
        self.websocket_start()

    @work(exclusive=True, thread=True)
    async def websocket_start(self):
        global app_is_closing

        async with websockets.connect(URI) as websocket:
            await websocket.send(json.dumps({
                'username': 'user1',
                'password': 'user1'
            }))

            await websocket.recv()

            await asyncio.gather(self.listen_server(websocket),
                                 self.send_message_on_server(websocket))

    async def send_message_on_server(self, websocket: websockets):
        global waiting_message

        while True:
            if len(waiting_message):
                for message in waiting_message:
                    await websocket.send(message)

                waiting_message.clear()

            await asyncio.sleep(0.1)

    async def listen_server(self, websocket: websockets):
        while True:
            if app_is_closing:
                self.query_one(Input).value = str(app_is_closing)
                await websocket.close()
                await websocket.send('close')

            try:
                recv = await asyncio.wait_for(websocket.recv(), timeout=1)

                if len(recv) <= 1:
                    continue

                type_recv, js = recv[0], json.loads(recv[1:])

                match type_recv:
                    case '0':
                        await self.get_new_message(js)
                    case '1':
                        await self.get_online_status(js)
                    case '2':
                        await self.get_new_user(js)
                    case '3':
                        await self.delete_message(js)

            except TimeoutError:
                pass

    async def get_new_message(self, js: json):
        global messages_list

        messages_list.append(Message(js['ID'], await self.find_user(js['OwnerID']),
                                     js['Message'], js['Date']))

        await self.query_one("#message_container").mount(messages_list[-1])
        messages_list[-1].scroll_visible(speed=0.0000000001)

    async def find_user(self, id: int):
        global users_list

        for user in users_list:
            if user.id_user == id:
                return user.username

    async def get_online_status(self, js: json):
        global users_list

        for i in range(len(users_list)):
            if users_list[i].id_user == js['ID']:
                users_list[i].change_online_status(js['OnlineStatus'])

        # if
        # for message in self.query(Message):
        #    if message.id_message == js['ID']:
        #        await message.remove()

    async def get_new_user(self, js: json):
        global users_list

        users_list.append(User(js['ID'], js['Name'], js['OnlineStatus']))

        await self.query_one("#user_container").mount(users_list[-1])
        users_list[-1].scroll_visible(speed=0.0000000001)

    async def delete_message(self, js: json):
        global messages_list

        await self.query_one(f'message_{js['ID']}').remove()

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield Header(name='MAGNET1C H1LLS CHAT')
        yield Footer()

        user_container = ScrollableContainer(id='user_container')
        user_container.styles.width = 20

        message_container = ScrollableContainer(id='message_container')

        yield Container(
            Horizontal(
                user_container,
                message_container
            )
        )

        yield Input(id='input', placeholder='Введите сообщение')

    def key_enter(self, event: events.Key):
        global waiting_message

        waiting_message.append(json.dumps({
            'OwnerID': current_user_id,
            'Message': self.query_one(Input).value
        }))

        self.query_one(Input).value = ''

    def action_close(self):
        global app_is_closing

        app_is_closing = True
        self.bell()


if __name__ == "__main__":
    app = ChatApp()
    app.run()
