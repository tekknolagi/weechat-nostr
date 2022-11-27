#!/usr/bin/env python

import asyncio
import bip340
import hashlib
import json
import signal
import sys
import ssl
import time
import uuid
import websocket
import weechat


# TODO(you) Fill in your privkey! It must be 32 bytes long.
PRIVKEY = b"x" * 32

PUBKEY = bip340.pubkey_gen(PRIVKEY)
SUBSCRIPTION_ID = str(uuid.uuid4())
SERVER = "wss://nostr-pub.wellorder.net"


class EventKind:
    set_metadata = 0
    text_note = 1
    recommend_server = 2


def slim_json_dump(obj):
    return json.dumps(obj, separators=(",", ":"))


def hash_json_of(obj):
    serialized_utf8 = slim_json_dump(obj).encode("utf-8")
    return hashlib.sha256(serialized_utf8).digest()


def sign(obj):
    assert isinstance(obj, bytes)
    raw_sig = bip340.schnorr_sign(obj, PRIVKEY, aux_rand=b"x" * 32)
    return raw_sig.hex()


def make_request(subscription_id, filters_json=None):
    return slim_json_dump(["REQ", subscription_id, filters_json or {}])


def make_event(content):
    pubkey = PUBKEY.hex()
    created_at = int(time.time())
    kind = EventKind.text_note
    tags = []
    assert isinstance(content, str)
    assert all(isinstance(tag, str) for tag in tags)
    serialized = [
        0,
        pubkey,
        created_at,
        kind,
        tags,
        content,
    ]
    event_id = hash_json_of(serialized)
    sig = sign(event_id)
    return {
        "id": event_id.hex(),
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": sig,
    }


def make_event_message(event):
    return slim_json_dump(["EVENT", event])


def buffer_close_cb(data, buffer):
    weechat.prnt(weechat.current_buffer(), "Goodbye.")
    return weechat.WEECHAT_RC_OK


def short_id(pubkey, length=8):
    return pubkey[: length // 2] + "..." + pubkey[-length // 2 :]


class Router:
    def __init__(self, ws, buffer):
        self.ws = ws
        self.buffer = buffer

    def receive_ws_callback(self, data, fd):
        # TODO(max): Why is this a loop?
        while True:
            try:
                # Read the data from the websocket associated with this team.
                opcode, data = self.ws.recv_data(control_frame=True)
            except ssl.SSLWantReadError:
                # No more data to read at this time.
                return weechat.WEECHAT_RC_OK
            except (websocket.WebSocketConnectionClosedException, socket.error) as e:
                self.handle_socket_error(e, data, "receive")
                return weechat.WEECHAT_RC_OK

            if opcode == websocket.ABNF.OPCODE_PONG:
                # team.last_pong_time = time.time()
                return weechat.WEECHAT_RC_OK
            elif opcode != websocket.ABNF.OPCODE_TEXT:
                return weechat.WEECHAT_RC_OK

            self.display_message(data)
            break
        return weechat.WEECHAT_RC_OK

    def display_message(self, data):
        message_raw = data.decode("utf-8")
        message_json = json.loads(message_raw)
        ty = message_json[0]
        if ty == "EVENT":
            event = message_json[2]
            sender = short_id(event["pubkey"])
            message = event["content"]
            kind = event["kind"]
            created_at = event["created_at"]
            if kind == EventKind.text_note:
                tags = "notify_message,nick_%s,prefix_nick_%s,log1" % (
                    sender,
                    weechat.config_string(
                        weechat.config_get("weechat.color.chat_nick_self")
                    ),
                )
                msg = "%s%s\t%s" % (
                    weechat.color("chat_nick_self"),
                    sender,
                    message,
                )
                weechat.prnt_date_tags(self.buffer, created_at, tags, msg)
        else:
            weechat.prnt(self.buffer, message_raw)

    def buffer_input_cb(self, data, buffer, input_data):
        # Sending the message should also trigger the receive hook, which will add
        # it to the buffer.
        event = make_event_message(make_event(input_data))
        self.ws.send(event)
        return weechat.WEECHAT_RC_OK


def main():
    weechat.register(
        "nostr", "Max B", "0.0", "MIT", "Use weechat as a nostr client", "", ""
    )
    buffer = weechat.buffer_new("nostr", "buffer_input_cb", "", "buffer_close_cb", "")
    weechat.buffer_set(buffer, "title", "nostr buffer")

    server = SERVER
    ws = websocket.create_connection(server)

    # This boundmethod trick allows us to keep context in the router for the
    # callbacks
    limit = 100
    router = Router(ws, buffer)
    global receive_ws_callback
    receive_ws_callback = router.receive_ws_callback
    global buffer_input_cb
    buffer_input_cb = router.buffer_input_cb
    weechat.hook_fd(
        ws.sock.fileno(),
        1,
        0,
        0,
        "receive_ws_callback",
        "",
    )
    ws.sock.setblocking(0)
    # TODO(max): Figure out how to receive the message backlog in the opposite
    # order. Right now it's sorted new->old, which makes for a confusing
    # message history because weechat will append to the bottom (oldest) as new
    # messages roll in later.
    ws.send(make_request(SUBSCRIPTION_ID, {"limit": limit, "since": 1669524090}))


if __name__ == "__main__":
    # TODO(max): Add commands to connect to server, set initial subscription
    # limit, query filters, etc
    main()
