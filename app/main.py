"""
Entry point.

Runs the Discord bot and the FastAPI web server concurrently on the same
asyncio event loop. Heroku requires a web dyno to bind to $PORT; uvicorn
handles that while the bot maintains the Discord WebSocket connection.

Usage:
    python3 -m app.main
"""

import asyncio
import os

import uvicorn

from app.config import settings
from app.services.thread_store import ThreadStore
from app.services.openai_service import OpenAIService
from app.bot import create_bot
from app.api import create_app


async def main():
    # --- Shared services ---
    thread_store = ThreadStore(db_path=settings.THREADS_DB_PATH)
    await thread_store.init()

    openai_service = OpenAIService(thread_store=thread_store)

    # --- Discord bot ---
    bot = create_bot(openai_service)

    # --- FastAPI ---
    fastapi_app = create_app(openai_service)
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn_config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(uvicorn_config)

    # Run both concurrently; either crashing will propagate to the other
    await asyncio.gather(
        bot.start(settings.DISCORD_KEY),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
