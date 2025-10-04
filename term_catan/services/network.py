from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator, Optional

import websockets


class NetworkService:
    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
        self.host = host
        self.port = port

    async def host_server(self) -> None:
        async def handler(ws):  # type: ignore[no-untyped-def]
            async for _message in ws:
                # Echo server for now
                await ws.send(_message)

        async with websockets.serve(handler, self.host, self.port):
            await asyncio.Future()  # run forever

    async def connect(self) -> AsyncIterator[websockets.WebSocketClientProtocol]:
        uri = f"ws://{self.host}:{self.port}"
        async with websockets.connect(uri) as ws:
            yield ws

    @staticmethod
    async def send_state(ws: websockets.WebSocketClientProtocol, state: dict) -> None:
        await ws.send(json.dumps(state))

    @staticmethod
    async def recv_state(ws: websockets.WebSocketClientProtocol) -> dict:
        msg = await ws.recv()
        return json.loads(msg)

