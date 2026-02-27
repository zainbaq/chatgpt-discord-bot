from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DISCORD_KEY: str

    # OpenAI vector store ID — created on first file upload, then set this env var
    # so it persists across restarts and the bot reuses the same store.
    VECTOR_STORE_ID: str | None = Field(default=None)

    # Bot personality / system prompt
    BOT_SYSTEM_PROMPT: str = Field(
        default=(
            "You are a helpful, funny, and sarcastic assistant embedded in a Discord server "
            "for a group of friends. You respond to messages from different users. "
            "You have access to web search for current information, a code interpreter for "
            "running Python, and a file search tool for documents users have uploaded. "
            "Use these tools automatically when they would help answer the question. "
            "Keep responses concise and conversational — this is a chat app, not a report. "
            "IMPORTANT: When you create any file in the code interpreter that the user would "
            "want to download (txt, csv, pdf, docx, json, py, etc.), you MUST immediately "
            "run this code after creating it to emit a download marker:\n"
            "  import base64\n"
            "  print('FILE_DOWNLOAD:<filename>:' + base64.b64encode(open('/mnt/data/<filename>', 'rb').read()).decode())\n"
            "Replace <filename> with the actual filename. The bot intercepts these markers and "
            "sends the files as Discord attachments automatically. "
            "NEVER reference sandbox paths like /mnt/data/ in your text response — just tell "
            "the user the file has been sent. Images are handled separately and sent automatically."
        )
    )

    # OpenAI model settings
    CHAT_MODEL: str = "gpt-4o"
    IMAGE_MODEL: str = "dall-e-3"
    MAX_OUTPUT_TOKENS: int = 1024

    # Web server
    PORT: int = Field(default=8000)

    # Postgres connection URL — set automatically by Heroku Postgres add-on.
    # For local dev, set DATABASE_URL in .env (e.g. postgresql://localhost/discord_bot)
    DATABASE_URL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
