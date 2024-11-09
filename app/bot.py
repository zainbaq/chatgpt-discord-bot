import openai
import discord
from discord.ext import commands
import argparse
import os
import io
import requests
from dotenv import load_dotenv
from rag import ConversationVectorStore

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', action='store_true')
    return parser.parse_args()

def load_keys():
    if '.env' in os.listdir():
        load_dotenv()
    return os.environ['OPENAI_KEY'], os.environ['DISCORD_KEY']

def create_vector_store():
    return ConversationVectorStore()

if __name__ == '__main__':

    args = parse_args()

    # Load API Keys
    openai_api_key, discord_api_key = load_keys()

    # Input your API Key here
    openai.api_key = openai_api_key

    intents = discord.Intents.default()
    intents.members = True

    HISTORY_LENGTH = 32
    RETENTION_LENGTH = 8

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
    async def on_memory_full(history_limit=20, retention=5):
        global MESSAGES
        if len(MESSAGES) > history_limit:
            retained_messages = [MESSAGES[0]] + MESSAGES[-retention:]
            MESSAGES = retained_messages
    
    # This function runs when an image generation is requested.
    @client.event
    async def dalle_response(message, n=1):
        prompt = message.content.split('.dalle ')[-1]
        response = openai.Image.create(
            prompt=prompt,
            n=n,
            size="1024x1024"
            )
        url = response['data'][0]['url'] # must be an image
        image_rsp = requests.get(url)
        image = io.BytesIO(image_rsp.content)
        await message.channel.send(file=discord.File(image, "generated_image.png"))

    # This function runs when a chat response is requested
    @client.event
    async def chat_response(message):
        # Make call to get AI response
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=MESSAGES
        )

        # Format AI response and add to conversation history
        ai_message = response['choices'][0]['message']['content']
        response = {"role": "assistant", "content": ai_message}
        MESSAGES.append(response)

        await message.channel.send(ai_message)

    @client.event
    async def on_message(message):
        print(message)
        global MESSAGES

        # Do nothing if bot mentions itself
        if message.author == client.user:
            return
        
        if client.user in message.mentions:

            # Get author and print mesage
            # print(f"{message.author} : {message.content}")
            author = message.author.name.split('#')[0]
            
            # Here we set up the prompt for the chat bot. We're including the message author so
            # it remembers who said what when multiple users are speaking
            prompt = f"{author} : {message.content}"



            prompt_data = {"role": "user", "content": prompt}

            MESSAGES.append(prompt_data)

            if '.dalle' in message.content:
                await dalle_response(message)
            elif '.clear' in message.content:
                MESSAGES = [MESSAGES[0]]
                await message.channel.send("These violent delights have violent ends.")
            else:
                await chat_response(message)

            await on_memory_full(history_limit=HISTORY_LENGTH, retention=RETENTION_LENGTH)
            
    client.run(discord_api_key)