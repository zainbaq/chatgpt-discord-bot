"""
Downloads Discord attachment files and classifies them for the OpenAI pipeline.

Images → passed as CDN URLs directly to the vision model (no upload needed).
Documents → downloaded and uploaded to the OpenAI Files API for RAG / code_interpreter.
"""

import aiohttp


async def download_attachment(url: str) -> tuple[bytes, str]:
    """
    Download a Discord CDN attachment.

    Returns:
        (file_bytes, filename) tuple.
    """
    filename = url.split("?")[0].rstrip("/").split("/")[-1]
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.read()
    return data, filename
