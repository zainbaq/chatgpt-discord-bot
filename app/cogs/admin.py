"""
AdminCog — operator-facing slash commands.

/status  — public info about the bot's current state.
/reload  — hot-reload all cogs without restarting (bot owner only).
"""

import time
import discord
from discord import app_commands
from discord.ext import commands

from app.services.openai_service import OpenAIService
from app.config import settings

# Recorded at import time so /status can report uptime
_START_TIME = time.time()


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, openai_service: OpenAIService):
        self.bot = bot
        self.openai = openai_service

    @app_commands.command(name="status", description="Show bot status and stats.")
    async def status(self, interaction: discord.Interaction):
        uptime_s = int(time.time() - _START_TIME)
        hours, remainder = divmod(uptime_s, 3600)
        minutes, seconds = divmod(remainder, 60)

        thread_count = await self.openai.thread_store.count()
        file_count = await self.openai.list_vector_store_files()
        vs_id = self.openai.vector_store_id or "_none_"

        embed = discord.Embed(title="Bot Status", color=discord.Color.green())
        embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        embed.add_field(name="Model", value=settings.CHAT_MODEL, inline=True)
        embed.add_field(name="Active channel threads", value=str(thread_count), inline=True)
        embed.add_field(name="Vector store files", value=str(file_count), inline=True)
        embed.add_field(name="Vector store ID", value=vs_id, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="reload",
        description="Reload all cogs (bot owner only).",
    )
    async def reload(self, interaction: discord.Interaction):
        if interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message(
                "⛔ Only the bot owner can use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        errors: list[str] = []
        for ext in list(self.bot.extensions):
            try:
                await self.bot.reload_extension(ext)
            except Exception as e:
                errors.append(f"`{ext}`: {e}")

        if errors:
            await interaction.followup.send("⚠️ Some extensions failed to reload:\n" + "\n".join(errors))
        else:
            await interaction.followup.send("✅ All extensions reloaded.")


async def setup(bot: commands.Bot, openai_service: OpenAIService):
    await bot.add_cog(AdminCog(bot, openai_service))
