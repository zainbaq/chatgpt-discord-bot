"""
ChatCog — main interaction surface for the bot.

Triggers:
  @mention  — bot responds to any message that mentions it directly.

Slash commands:
  /image <prompt>  — generate an image with DALL-E 3.
  /clear           — reset the conversation history for this channel.
"""

import io
import discord
from discord import app_commands
from discord.ext import commands

from app.services.openai_service import OpenAIService
from app.services.file_service import download_attachment

# Discord's hard message length limit
DISCORD_MSG_LIMIT = 2000


class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot, openai_service: OpenAIService):
        self.bot = bot
        self.openai = openai_service

    # ------------------------------------------------------------------
    # @mention handler
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore own messages
        if message.author == self.bot.user:
            return

        # Only respond when directly @mentioned
        if self.bot.user not in message.mentions:
            return

        # Strip the @mention from the message content
        user_input = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
        if not user_input and not message.attachments:
            return

        image_urls: list[str] = []
        file_ids: list[str] = []

        # Process attachments before the main AI call
        if message.attachments:
            async with message.channel.typing():
                for attachment in message.attachments:
                    filename = attachment.filename.lower()
                    if self.openai.is_image(filename):
                        # Images passed as CDN URLs directly to the vision model
                        image_urls.append(attachment.url)
                    elif self.openai.is_document(filename):
                        # Documents uploaded to OpenAI Files API → vector store + code interpreter
                        try:
                            file_bytes, fname = await download_attachment(attachment.url)
                            file_id = await self.openai.upload_file(file_bytes, fname)
                            await self.openai.add_to_vector_store(file_id)
                            file_ids.append(file_id)
                        except Exception as e:
                            print(f"[ChatCog] Failed to upload {attachment.filename}: {e}")
                            await message.channel.send(
                                f"⚠️ Couldn't process `{attachment.filename}` — skipping it."
                            )

        # Show typing indicator while the AI thinks
        async with message.channel.typing():
            placeholder = await message.channel.send("_Thinking…_")
            try:
                result = await self.openai.chat(
                    channel_id=message.channel.id,
                    user_input=user_input or "(see attachments)",
                    image_urls=image_urls or None,
                    file_ids=file_ids or None,
                    username=message.author.display_name,
                )
            except Exception as e:
                print(f"[ChatCog] OpenAI error: {e}")
                await placeholder.edit(content="⚠️ Something went wrong. Please try again.")
                return

        # --- Send text response ---
        chunks = _split(result.text)
        await placeholder.edit(content=chunks[0])
        for chunk in chunks[1:]:
            await message.channel.send(chunk)

        # --- Send any images produced by the code interpreter ---
        for i, img_url in enumerate(result.output_image_urls):
            try:
                img_bytes = await self.openai.download_url(img_url)
                discord_file = discord.File(io.BytesIO(img_bytes), filename=f"output_{i + 1}.png")
                await message.channel.send(file=discord_file)
            except Exception as e:
                print(f"[ChatCog] Failed to send code interpreter image: {e}")
                await message.channel.send(f"⚠️ Couldn't send generated image #{i + 1}.")

        # --- Send DALL-E images generated inline via the generate_image function tool ---
        for i, img_bytes in enumerate(result.output_images):
            try:
                discord_file = discord.File(io.BytesIO(img_bytes), filename=f"image_{i + 1}.png")
                await message.channel.send(file=discord_file)
            except Exception as e:
                print(f"[ChatCog] Failed to send DALL-E image: {e}")
                await message.channel.send(f"⚠️ Couldn't send generated image #{i + 1}.")

    # ------------------------------------------------------------------
    # Slash: /image
    # ------------------------------------------------------------------

    @app_commands.command(name="image", description="Generate an image with DALL-E 3.")
    @app_commands.describe(prompt="What to generate")
    async def image(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer(thinking=True)
        try:
            # Download immediately — DALL-E CDN URLs expire after ~1 hour
            img_bytes = await self.openai.generate_image(prompt)
        except Exception as e:
            print(f"[ChatCog] Image generation error: {e}")
            await interaction.followup.send("⚠️ Image generation failed. Please try again.")
            return

        discord_file = discord.File(io.BytesIO(img_bytes), filename="generated.png")
        await interaction.followup.send(f"**{prompt}**", file=discord_file)

    # ------------------------------------------------------------------
    # Slash: /clear
    # ------------------------------------------------------------------

    @app_commands.command(
        name="clear",
        description="Clear the conversation history for this channel.",
    )
    async def clear(self, interaction: discord.Interaction):
        await self.openai.clear_channel(interaction.channel_id)
        await interaction.response.send_message(
            "🗑️ Conversation history cleared for this channel.", ephemeral=True
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _split(text: str, limit: int = DISCORD_MSG_LIMIT) -> list[str]:
    """Split a string into chunks that fit within Discord's message limit."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


async def setup(bot: commands.Bot, openai_service: OpenAIService):
    await bot.add_cog(ChatCog(bot, openai_service))
