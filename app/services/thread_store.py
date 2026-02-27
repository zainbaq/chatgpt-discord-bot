"""
Persists the per-channel last_response_id so the bot can maintain multi-turn
conversation context across messages — and across Heroku deploys.

How it works:
  The OpenAI Responses API is stateless per-request, but supports chaining via
  `previous_response_id`. OpenAI stores the full conversation server-side; we
  only need to remember the last response ID for each channel.

Persistence:
  Heroku Postgres via asyncpg. The DATABASE_URL env var is set automatically
  by Heroku when the Postgres add-on is attached. Conversation chains persist
  across deploys and dyno restarts.
"""

import asyncpg


class ThreadStore:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def init(self):
        # Heroku Postgres requires SSL; skip SSL only for local connections.
        is_local = any(h in self.database_url for h in ("localhost", "127.0.0.1"))
        ssl = None if is_local else "require"
        self.pool = await asyncpg.create_pool(self.database_url, ssl=ssl)
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS channel_threads (
                channel_id  BIGINT PRIMARY KEY,
                response_id TEXT   NOT NULL,
                updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

    async def get(self, channel_id: int) -> str | None:
        row = await self.pool.fetchrow(
            "SELECT response_id FROM channel_threads WHERE channel_id = $1",
            channel_id,
        )
        return row["response_id"] if row else None

    async def set(self, channel_id: int, response_id: str):
        await self.pool.execute(
            """
            INSERT INTO channel_threads (channel_id, response_id, updated_at)
            VALUES ($1, $2, now())
            ON CONFLICT (channel_id) DO UPDATE SET
                response_id = EXCLUDED.response_id,
                updated_at  = now()
            """,
            channel_id,
            response_id,
        )

    async def delete(self, channel_id: int):
        await self.pool.execute(
            "DELETE FROM channel_threads WHERE channel_id = $1", channel_id
        )

    async def count(self) -> int:
        row = await self.pool.fetchrow("SELECT COUNT(*) FROM channel_threads")
        return row["count"] if row else 0
