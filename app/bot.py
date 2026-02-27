"""
Bot factory.

Creates the discord.py Bot instance, registers intents, and loads cogs via
setup_hook (which runs before the bot connects to Discord).
"""

import discord
from discord.ext import commands

from app.services.thread_store import ThreadStore
from app.services.openai_service import OpenAIService
from app.config import settings


def create_bot(openai_service: OpenAIService) -> commands.Bot:
    # Only request the intents we actually need
    intents = discord.Intents.default()
    intents.message_content = True  # Required to read message text for @mentions

    bot = commands.Bot(
        # Prefix only fires on @mention — slash commands are the primary interface
        command_prefix=commands.when_mentioned,
        intents=intents,
        help_command=None,
    )

    async def setup_hook():
        from app.cogs.chat import ChatCog
        from app.cogs.admin import AdminCog

        await bot.add_cog(ChatCog(bot, openai_service))
        await bot.add_cog(AdminCog(bot, openai_service))

        # Sync slash commands globally (can take up to 1 hour to propagate on first deploy;
        # use guild-scoped sync during development for instant updates).
        await bot.tree.sync()
        print(f"[Bot] Slash commands synced. Logged in as {bot.user}")

    bot.setup_hook = setup_hook

    @bot.event
    async def on_ready():
        print(f"[Bot] Ready — {bot.user} (id: {bot.user.id})")

    return bot
