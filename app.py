#!/usr/bin/env python

import asyncio
import json
import signal
import sys
import websockets
import uuid

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Static
from rich.json import JSON


SUBSCRIPTION_ID = str(uuid.uuid4())
SERVER = "wss://nostr-pub.wellorder.net"


def slim_json_dump(obj):
    return json.dumps(obj, separators=(",", ":"))


def make_request(subscription_id, filters_json=None):
    return slim_json_dump(["REQ", subscription_id, filters_json or {}])


def short_id(id):
    return id[:4] + "..." + id[-4:]


class Message(Static):
    pass


class Event(Message):
    pass


class Post(Event):
    def __init__(self, author, content):
        super().__init__(f"{author}: {content}")


def render_message(message):
    ty = message[0]
    if ty == "NOTICE":
        return Message(f"NOTICE: {message[1]}")
    if ty == "EVENT":
        _, subscription_id, event = message
        content = event["content"]
        return Post(short_id(event["id"]), content)
    return Message(message)


def order_msg(msg):
    ty = msg[0]
    if ty != "EVENT":
        return 0
    return msg[2]["created_at"]


class Demo(App):
    "A title"
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit the app"),  # built-in
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Container(id="messages")

    def display_message(self, message):
        messages = self.query_one("#messages")
        messages.mount(render_message(message))

    async def fetch_messages(self):
        messages = self.query_one("#messages")
        async for message in self.websocket:
            # TODO(max): Figure out how to scroll to the bottom on new messages
            self.display_message(json.loads(message))

    async def fetch_initial_messages(self):
        messages = self.query_one("#messages")
        received = []
        async for message in self.websocket:
            j = json.loads(message)
            if j[0] == "EOSE":
                break
            received.append(j)
        for msg in sorted(received, key=order_msg):
            messages.mount(render_message(msg))
        asyncio.create_task(self.fetch_messages())

    async def on_mount(self) -> None:
        messages = self.query_one("#messages")
        self.websocket = await websockets.connect(SERVER)
        messages.mount(Message("...connected!"))
        await self.websocket.send(make_request(SUBSCRIPTION_ID, {"limit": 100}))
        messages.mount(Message("...subscribed!"))
        asyncio.create_task(self.fetch_initial_messages())
        messages.mount(Message("...now fetching!"))

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark


if __name__ == "__main__":
    app = Demo()
    app.run()
