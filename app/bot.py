import discord
from discord.ext import commands
import argparse
import io
import requests
from openai import OpenAI
from utils import *

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', action='store_true')
    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    # Load API Keys
    openai_api_key, discord_api_key = load_keys()

    # Input your API Key here
    openai_client = OpenAI()

    intents = discord.Intents.default()
    intents.members = True

    HISTORY_LENGTH = 8
    RETENTION_LENGTH = 2

    vectorstore = create_vector_store()
    
    # Set the system role of the assistant
    role = """
    You are a helpful, funny and sarcastic assistant to a group of individuals.

    You will receive questions from different users. Answer these questions to the best of your knowledge.

    ** EXAMPLE INPUT **
    <CONTEXT>
    <USER_123> : When did Pakistan gain independence?

    ** EXAMPLE OUTPUT **
    Pakistan gained independence on the 14th of August 1947.

    You may be asked about other users and your goal is to be a part of our group.
    """

    # Discord bot
    client = commands.Bot(command_prefix='!', intents=intents)

    MESSAGES = [{"role": "system", "content": role}]

    @client.event
    async def on_ready():
        # Standby function
        print('Bot is ready.')

    # This function runs when the conversation length limit is reached.
    @client.event
    async def on_memory_full(history_limit=3, retention=1):
        global MESSAGES
        global vectorstore

        print(f"len messages: {len(MESSAGES)}, limit: {history_limit}")
        if len(MESSAGES) >= history_limit:
            print('here now')
            messages_to_store = MESSAGES[1:-retention]
            retained_messages = [MESSAGES[0]] + MESSAGES[-retention:]

            messages_to_store = [prepare_vector_input(m) for m in messages_to_store]

            vectorstore.insert_conversation_to_memory(messages_to_store)

            MESSAGES = retained_messages
    
    # This function runs when an image generation is requested.
    @client.event
    async def image_response(message, n=1):
        response = openai_client.images.generate(
            model='gpt-4o',
            prompt=message.content,
            n=n,
            size="1024x1024"
            )
        url = response['data'][0]['url'] # must be an image
        image_rsp = requests.get(url)
        image = io.BytesIO(image_rsp.content)
        await message.channel.send(file=discord.File(image, "generated_image.png"))


    # This function runs when a chat response is requested
    @client.event
    async def chat_response(message, context):

        image_urls = []
        if message.attachments:
            for attachment in message.attachments:
                print(attachment.content_type)
                if 'image' in attachment.content_type:
                    image_urls.append(attachment.url)

        if len(image_urls) != 0:
            prompt_data = create_image_analysis_prompt(message, image_urls, context)
        else:
            prompt_data = create_chat_prompt(message, context)

        MESSAGES.append(prompt_data)

        # Make call to get AI response
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=MESSAGES,
            max_tokens=150
        )

        # Format AI response and add to conversation history
        ai_message = response.choices[0].message.content
        response = {"role": "assistant", "content": ai_message}
        MESSAGES.append(response)

        await message.channel.send(ai_message)

    @client.event
    async def on_message(message):
        global MESSAGES
        global vectorstore

        # Do nothing if bot mentions itself
        if message.author == client.user:
            return
        
        if client.user in message.mentions:

            # Get author and print mesage
            # print(f"{message.author} : {message.content}")
            author = message.author.name.split('#')[0]
            
            # Here we set up the prompt for the chat bot. We're including the message author so
            # it remembers who said what when multiple users are speaking

            create_image = route_user_message(message.content)

            if create_image:
                await image_response(message)
            elif '.clear' in message.content:
                MESSAGES = [MESSAGES[0]]
                await message.channel.send("These violent delights have violent ends.")
            else:
                query_result = vectorstore.query("conversations", message.content, n_results=5)
                context = parse_context(query_result)
                await chat_response(message, context)

            await on_memory_full(history_limit=HISTORY_LENGTH, retention=RETENTION_LENGTH)
            
    client.run(discord_api_key)