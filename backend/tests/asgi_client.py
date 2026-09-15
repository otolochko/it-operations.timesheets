"""Small synchronous facade over HTTPX's async ASGI transport for tests.

Starlette's synchronous TestClient runs an AnyIO blocking portal.  In this
project's Python 3.12 environment that portal deadlocks after SQLAlchemy is
imported, while the async ASGI transport is unaffected.  Keeping the adapter
here means route tests still exercise the full ASGI stack without opening a
network listener or scheduler lifespan.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx


class ASGITestClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        async def send_request() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                return await client.request(method, url, **kwargs)

        return asyncio.run(send_request())

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)
