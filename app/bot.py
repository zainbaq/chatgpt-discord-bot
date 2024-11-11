import discord  # Discord API for interacting with Discord
from discord.ext import commands  # Extension for Discord commands
import argparse  # For parsing command-line arguments
import io  # For handling byte streams
import requests  # For making HTTP requests
from openai import OpenAI  # OpenAI API client
from utils import *  # Custom utility functions

def parse_args():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', action='store_true')
    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    # Load API Keys from external source
    openai_api_key, discord_api_key = load_keys()

    # Initialize OpenAI client with API key
    openai_client = OpenAI(api_key=openai_api_key)

    # Set up Discord intents
    intents = discord.Intents.default()
    intents.members = True  # Enable access to member data

    # Conversation history settings
    HISTORY_LENGTH = 8  # Max length of conversation history before storing
    RETENTION_LENGTH = 2  # Number of recent messages to retain

    # Initialize vector store for long-term conversation memory
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

    # Initialize Discord bot with command prefix and intents
    client = commands.Bot(command_prefix='!', intents=intents)

    # Initialize message history with system role
    MESSAGES = [{"role": "system", "content": role}]

    @client.event
    async def on_ready():
        """Event handler when the bot is ready."""
        print('Bot is ready.')

    @client.event
    async def on_memory_full(history_limit=HISTORY_LENGTH, retention=RETENTION_LENGTH):
        """
        Handles memory management when conversation history exceeds limit.
        Stores old messages in vector store and retains recent messages.

        Args:
            history_limit (int): Max length of conversation history before storing.
            retention (int): Number of recent messages to retain.
        """
        global MESSAGES
        global vectorstore

        if len(MESSAGES) >= history_limit:
            print('Storing old messages to vector store and trimming history.')
            # Extract messages to store and messages to retain
            messages_to_store = MESSAGES[1:-retention]  # Exclude system prompt and retain last messages
            retained_messages = [MESSAGES[0]] + MESSAGES[-retention:]  # Keep system prompt and last messages

            # Prepare messages for vector store
            prepared_messages = [prepare_vector_input(m) for m in messages_to_store]

            # Insert old messages into vector store
            vectorstore.insert_conversation_to_memory(prepared_messages)

            # Update MESSAGES with retained messages
            MESSAGES = retained_messages

    @client.event
    async def image_response(message, n=1):
        """
        Generates an image based on the user's prompt and sends it to the channel.

        Args:
            message (discord.Message): The message containing the prompt.
            n (int): Number of images to generate.
        """
        try:
            response = openai_client.images.generate(
                model='dall-e-3',
                prompt=message.content,
                n=n,
                size="1024x1024"
            )
            url = response.data[0].url  # URL of the generated image
            image_rsp = requests.get(url)
            image = io.BytesIO(image_rsp.content)
            await message.channel.send(file=discord.File(image, "generated_image.png"))
        except Exception as e:
            await message.channel.send("Sorry, I couldn't generate the image.")
            print(f"Error generating image: {e}")

    @client.event
    async def chat_response(message, context):
        """
        Generates a chat response based on the user's message and context.

        Args:
            message (discord.Message): The message from the user.
            context (str): The context retrieved from the vector store.
        """
        image_urls = []
        if message.attachments:
            # Check for image attachments and collect URLs
            for attachment in message.attachments:
                if attachment.content_type and 'image' in attachment.content_type:
                    image_urls.append(attachment.url)

        if image_urls:
            # Create prompt for image analysis
            prompt_data = create_image_analysis_prompt(message, image_urls, context)
        else:
            # Create standard chat prompt
            prompt_data = create_chat_prompt(message, context)

        # Add user's prompt to message history
        MESSAGES.append(prompt_data)

        try:
            # Make call to get AI response
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=MESSAGES,
                max_tokens=150
            )

            # Extract AI response and add to conversation history
            ai_message = response.choices[0].message.content
            response_message = {"role": "assistant", "content": ai_message}
            MESSAGES.append(response_message)

            # Send AI response to channel
            await message.channel.send(ai_message)
        except Exception as e:
            await message.channel.send("Sorry, I couldn't process your request.")
            print(f"Error generating chat response: {e}")

    @client.event
    async def on_message(message):
        """
        Event handler for incoming messages.
        Processes messages that mention the bot and routes them accordingly.

        Args:
            message (discord.Message): The incoming message.
        """
        global MESSAGES
        global vectorstore

        # Ignore messages from the bot itself
        if message.author == client.user:
            return

        # Check if the bot is mentioned in the message
        if client.user in message.mentions:

            # Extract author's name (excluding discriminator)
            author = message.author.name

            # Determine if an image should be created based on the message content
            create_image = route_user_message(message.content)

            if create_image:
                # Handle image generation
                await image_response(message)
            elif '.clear' in message.content.lower():
                # Clear conversation history except system prompt
                MESSAGES = [MESSAGES[0]]
                await message.channel.send("Conversation history cleared.")
            else:
                # Retrieve context from vector store based on user's message
                query_result = vectorstore.query("conversations", message.content, n_results=5)
                context = parse_context(query_result)

                # Generate chat response with context
                await chat_response(message, context)

            # Manage conversation history to prevent exceeding limits
            await on_memory_full()

    # Run the bot with the Discord API key
    client.run(discord_api_key)