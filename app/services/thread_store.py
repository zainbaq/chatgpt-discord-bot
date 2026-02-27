"""
Persists the per-channel last_response_id so the bot can maintain multi-turn
conversation context across messages within a session.

How it works:
  The OpenAI Responses API is stateless per-request, but supports chaining via
  `previous_response_id`. OpenAI stores the full conversation server-side; we
  only need to remember the last response ID for each channel.

Persistence:
  SQLite file (app/data/threads.db). Survives within a running process/dyno
  session. Resets on bot restart or Heroku deploy, which causes conversations
  to start fresh — acceptable for a casual Discord bot. Uploaded files and the
  vector store persist independently on OpenAI's servers.
"""

import aiosqlite
import os
from datetime import datetime


class ThreadStore:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_threads (
                    channel_id  INTEGER PRIMARY KEY,
                    response_id TEXT    NOT NULL,
                    updated_at  TEXT    NOT NULL
                )
                """
            )
            await db.commit()

    async def get(self, channel_id: int) -> str | None:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT response_id FROM channel_threads WHERE channel_id = ?",
                (channel_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set(self, channel_id: int, response_id: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO channel_threads (channel_id, response_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    response_id = excluded.response_id,
                    updated_at  = excluded.updated_at
                """,
                (channel_id, response_id, datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def delete(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM channel_threads WHERE channel_id = ?",
                (channel_id,),
            )
            await db.commit()

    async def count(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM channel_threads") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
