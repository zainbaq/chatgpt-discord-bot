# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

**Create and activate the virtual environment (first time):**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Start locally:**
```bash
source venv/bin/activate
python3 -m app.main
```

This starts both the Discord bot and the FastAPI server on the same process. The FastAPI server binds to `PORT` (default `8000`). Verify with `curl localhost:8000/health`.

**Required `.env` file at project root:**
```
OPENAI_API_KEY=...
DISCORD_KEY=...
VECTOR_STORE_ID=...    # Optional — set after first file upload to reuse the store across restarts
```

## Architecture

The bot uses **OpenAI Responses API** (not Chat Completions or Assistants) for all agentic chat. A **FastAPI** web server runs alongside the Discord bot in the same asyncio event loop, required for Heroku's `web` dyno to stay alive.

### File layout
```
app/
├── main.py               # Entry point — asyncio.gather(bot, uvicorn)
├── bot.py                # Bot factory: intents, cog loading via setup_hook
├── api.py                # FastAPI: /health, /status
├── config.py             # Pydantic Settings — all env vars live here
├── cogs/
│   ├── chat.py           # on_message (@mention), /image, /clear
│   └── admin.py          # /status, /reload (owner only)
└── services/
    ├── thread_store.py   # SQLite persistence of channel_id → last_response_id
    ├── openai_service.py # Responses API wrapper; image gen; file upload; vector store
    └── file_service.py   # Downloads Discord CDN attachments
```

### How conversation memory works

The Responses API is stateless per-request but supports chaining via `previous_response_id`. OpenAI stores the full conversation server-side; we only persist the **last `response_id` per channel** in `app/data/threads.db` (SQLite via `aiosqlite`). On each `chat()` call, `ThreadStore.get(channel_id)` fetches the ID, it's passed as `previous_response_id`, and the new response ID is saved back.

Memory survives within a running session. After a bot restart or Heroku deploy, channel threads start fresh (SQLite is ephemeral on Heroku). Uploaded files and the vector store persist on OpenAI's servers indefinitely.

### Agentic tools (always active in chat)

| Tool | What it does |
|---|---|
| `web_search_preview` | Real-time web search with citations |
| `code_interpreter` | Sandboxed Python execution |
| `file_search` | Semantic RAG over uploaded documents (requires `VECTOR_STORE_ID`) |

DALL-E 3 image generation is triggered via the `/image` slash command.

### How file uploads work

1. User attaches a file when @mentioning the bot
2. `ChatCog.on_message` classifies by extension: **image** (png/jpg/gif/webp) or **document** (pdf/txt/md/docx/py/js/ts/csv/json)
3. Images → Discord CDN URL passed directly to the vision model
4. Documents → downloaded via `file_service.download_attachment`, uploaded to OpenAI Files API, added to the shared vector store
5. On first upload, `OpenAIService` creates the vector store and prints its ID — set `VECTOR_STORE_ID` in your env to reuse it across restarts

### Discord interaction

- Bot responds only when @mentioned
- Slash commands: `/image <prompt>`, `/clear`, `/status`, `/reload`
- Long responses are split into multiple messages at the 2000-character Discord limit
- A `_Thinking…_` placeholder is sent immediately and edited with the final response

## Deployment (Heroku)

**Procfile:**
```
web: python3 -m app.main
```

Uses a `web` dyno (not `worker`) because FastAPI binds to Heroku's `$PORT`. Set all required env vars in Heroku Config Vars (Settings → Config Vars). After first use with file uploads, copy the printed `VECTOR_STORE_ID` into Config Vars so the store persists across deploys.

**Set default branch to `main` on GitHub:**
GitHub → repo Settings → Branches → change default from `master` to `main`.
