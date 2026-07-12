from __future__ import annotations

import logging
import os

from aiohttp import web

logger = logging.getLogger(__name__)


async def start_health_server() -> web.AppRunner:
    port = int(os.getenv("PORT", "8080"))

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health server listening on :%s", port)
    return runner
