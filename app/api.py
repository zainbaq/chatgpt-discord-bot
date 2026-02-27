"""
FastAPI application.

Provides HTTP endpoints required for Heroku web dyno health checks and
basic operational visibility. The bot process and this web server share
the same asyncio event loop (wired together in main.py).
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# openai_service is injected at startup from main.py so the /status endpoint
# can read live state without circular imports.
_openai_service = None


def create_app(openai_service=None):
    global _openai_service
    _openai_service = openai_service

    app = FastAPI(title="Discord Bot API", docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/status")
    async def status():
        if _openai_service is None:
            return JSONResponse({"error": "service not initialised"}, status_code=503)

        thread_count = await _openai_service.thread_store.count()
        file_count = await _openai_service.list_vector_store_files()

        return {
            "status": "ok",
            "model": _openai_service.client.base_url,
            "active_channel_threads": thread_count,
            "vector_store_files": file_count,
            "vector_store_id": _openai_service.vector_store_id,
        }

    return app
