"""
Interactive terminal chat for testing the bot's AI pipeline locally.

Uses the exact same OpenAIService and ThreadStore that the Discord bot uses,
so behaviour here matches what users will see in Discord.

Usage:
    source venv/bin/activate
    python3 test_chat.py

Commands inside the chat:
    /clear      — reset conversation history for this session
    /image <p>  — generate an image (prints the URL)
    /status     — show vector store and thread info
    /upload <path> — upload a local file to the vector store
    quit / exit — stop
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from app.services.thread_store import ThreadStore
from app.services.openai_service import OpenAIService
from app.config import settings

# Use a fake channel ID for the CLI session
CHANNEL_ID = 0


async def main():
    thread_store = ThreadStore(db_path=settings.THREADS_DB_PATH)
    await thread_store.init()
    svc = OpenAIService(thread_store=thread_store)

    print("Bot CLI — type your message, or /clear /image /upload /status to test features.")
    print("─" * 60)

    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not line:
            continue

        if line.lower() in ("quit", "exit"):
            break

        if line == "/clear":
            await svc.clear_channel(CHANNEL_ID)
            print("System: conversation cleared.\n")
            continue

        if line.startswith("/image "):
            prompt = line[7:].strip()
            print("System: generating image…")
            try:
                img_bytes = await svc.generate_image(prompt)
                out_path = "test_image_output.png"
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                print(f"Image saved to: {out_path} ({len(img_bytes)} bytes)\n")
            except Exception as e:
                print(f"Error: {e}\n")
            continue

        if line == "/status":
            count = await thread_store.count()
            files = await svc.list_vector_store_files()
            prev_id = await thread_store.get(CHANNEL_ID)
            print(f"  active threads (db): {count}")
            print(f"  current session response_id: {prev_id}")
            print(f"  vector store id: {svc.vector_store_id}")
            print(f"  vector store files: {files}\n")
            continue

        if line.startswith("/upload "):
            path = line[8:].strip()
            if not os.path.exists(path):
                print(f"Error: file not found: {path}\n")
                continue
            filename = os.path.basename(path)
            with open(path, "rb") as f:
                data = f.read()
            print(f"System: uploading {filename}…")
            try:
                file_id = await svc.upload_file(data, filename)
                await svc.add_to_vector_store(file_id)
                print(f"System: uploaded. file_id={file_id}\n")
            except Exception as e:
                print(f"Error: {e}\n")
            continue

        # Normal chat
        try:
            result = await svc.chat(
                channel_id=CHANNEL_ID,
                user_input=line,
                username="Tester",
            )
            print(f"\nBot: {result.text}\n")
            for i, img_url in enumerate(result.output_image_urls):
                out_path = f"test_code_output_{i + 1}.png"
                img_bytes = await svc.download_url(img_url)
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                print(f"[Code output image saved: {out_path}]\n")
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
