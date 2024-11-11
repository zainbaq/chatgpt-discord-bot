import os
import json
from dotenv import load_dotenv  # For loading environment variables from a .env file
from rag import ConversationVectorStore  # Custom module for vector storage
from openai import OpenAI  # OpenAI API client

# Load OpenAI API key if not already loaded
if 'OPENAI_API_KEY' not in os.environ:
    if '.env' in os.listdir():
        load_dotenv()

# Initialize OpenAI client globally to avoid recreating it in functions
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

def load_keys():
    """
    Load OpenAI and Discord API keys from environment variables.

    Returns:
        tuple: OpenAI API key and Discord API key.
    """
    # Check if .env file exists and load environment variables
    if '.env' in os.listdir():
        load_dotenv()
    return os.environ['OPENAI_API_KEY'], os.environ['DISCORD_KEY']

def create_vector_store():
    """
    Create an instance of the conversation vector store.

    Returns:
        ConversationVectorStore: Instance for storing and retrieving conversation data.
    """
    return ConversationVectorStore()

def prepare_vector_input(message):
    """
    Prepare a message for insertion into the vector store.

    Args:
        message (dict): A message dictionary with 'role' and 'content'.

    Returns:
        str: JSON string containing the author and message content.
    """
    role = message['role']
    content = message['content']

    if role == 'assistant':
        # If the message is from the assistant, set author accordingly
        author = 'assistant'
        query = content
    else:
        # Extract author and query from the user's message
        try:
            author, query = content.split(' : ', 1)
        except ValueError:
            # Handle cases where the split does not yield two elements
            author = 'unknown'
            query = content
    # Return the message as a JSON string
    return json.dumps({'author': author, 'message': query})

def parse_context(query_result):
    """
    Parse the context retrieved from the vector store.

    Args:
        query_result (dict): The result from the vector store query.

    Returns:
        list: List of parsed documents containing previous messages.
    """
    documents = query_result['documents']
    # Parse each document from JSON string to dictionary
    parsed_documents = [json.loads(s) for s in documents[0]]
    return parsed_documents

def create_chat_prompt(message, context):
    """
    Create a chat prompt for the assistant, including any relevant context.

    Args:
        message (discord.Message): The user's message object.
        context (list): List of previous conversation snippets.

    Returns:
        dict: The prompt data to be sent to the assistant.
    """
    # Extract author's name
    author = message.author.name
    # Extract the user's query, removing any mentions or prefixes
    user_query = message.content.split('> ')[-1].strip()
    # Format the prompt with context and user input
    prompt = f"""
    ** CONTEXT **
    {context}

    ** USER INPUT **
    {author} : {user_query}
    """
    prompt_data = {
        "role": "user",
        "content": prompt
    }
    return prompt_data

def create_image_analysis_prompt(message, image_urls, context):
    """
    Create a prompt for image analysis, including any relevant context and image URLs.

    Args:
        message (discord.Message): The user's message object.
        image_urls (list): List of image URLs attached to the message.
        context (list): List of previous conversation snippets.

    Returns:
        dict: The prompt data including images to be sent to the assistant.
    """
    # Extract author's name
    author = message.author.name
    # Extract the user's query
    user_query = message.content.split('> ')[-1].strip()

    # Format the prompt with context and user input
    prompt = f"""
    ** CONTEXT **
    {context}

    ** USER INPUT **
    {author} : {user_query}
    """
    # Create the content list with text and image URLs
    content = [{"type": "text", "text": prompt}] + \
              [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]

    prompt_data = {
        "role": "user",
        "content": content,
    }
    return prompt_data

def route_user_message(message):
    """
    Determine if the user's message is a request to generate an image.

    Args:
        message (str): The content of the user's message.

    Returns:
        bool: True if the message is an image generation request, False otherwise.
    """
    user_query = message.strip()

    # System prompt defining the assistant's task
    system_prompt = {
        "role": "system",
        "content": """
    ** INSTRUCTIONS **
    You will be given a piece of text and you need to determine if the text 
    contains a request to generate or create an image.

    Strictly follow the instructions below:

    If the user input contains a request to generate an image, return 'True'.
    Else return 'False'.

    ** EXAMPLE 1 USER INPUT **
    Create an image of a cat.

    ** EXAMPLE 1 OUTPUT **
    True

    ** EXAMPLE 2 USER INPUT **
    What is the weather like today?

    ** EXAMPLE 2 OUTPUT **
    False
    """
    }

    # User prompt containing the user's query
    prompt = {
        "role": "user",
        "content": f"""
    ** USER INPUT **
    {user_query}
    """
    }

    input_data = [system_prompt, prompt]

    try:
        # Call OpenAI API to classify the user's message
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=input_data,
            max_tokens=8,
            temperature=0  # Set temperature to 0 for deterministic output
        ).choices[0].message.content.strip()
    except Exception as e:
        print(f"Error in route_user_message: {e}")
        return False

    # Return True if the response is 'True', else False
    return response == 'True'