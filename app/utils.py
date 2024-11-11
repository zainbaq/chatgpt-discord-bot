from dotenv import load_dotenv
from rag import ConversationVectorStore
import os
import json
from openai import OpenAI

def load_keys():
    if '.env' in os.listdir():
        load_dotenv()
    return os.environ['OPENAI_API_KEY'], os.environ['DISCORD_KEY']

def create_vector_store():
    return ConversationVectorStore()

def prepare_vector_input(message):
    print(message['content'])
    role = message['role']
    if role == 'assistant':
        author = 'assistant'
        query = message['content']
    else:
        author, query = message['content'].split(' : ')
    return json.dumps({'author' : author, 'message': query})

def parse_context(query_result):
    ids = query_result['ids']
    documents = query_result['documents']
    documents = [json.loads(s) for s in documents[0]]
    return documents


def create_chat_prompt(message, context):
    author = message.author.name.split('#')[0]
    user_query = message.content.split('> ')[-1]
    prompt = f"""
    ** CONTEXT **
    {context}

    ** USER INPUT **
    {author} : {user_query}"
    """
    prompt_data = {
        "role": "user", 
        "content": prompt
        }
    return prompt_data

def create_image_analysis_prompt(message, image_urls, context):
    author = message.author.name.split('#')[0]
    user_query = message.content.split('> ')[-1]

    prompt = f"""
    ** CONTEXT **
    {context}

    ** USER INPUT **
    {author} : {user_query}"
    """
    
    prompt_data = {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt}] + [{"type":"image_url","image_url": {"url":url}} for url in image_urls],
    }
    return prompt_data

def route_user_message(message):
    client = OpenAI()

    # author = message.author.name.split('#')[0]
    # user_query = message.content.split('> ')[-1]
    user_query = message
    
    prompt = {
        "role": "user", 
        "content": f"""
            ** USER INPUT **
            {user_query}"
            """
    }

    system_prompt = {
        "role" : "assistant",
        "content" : """

        ** INSTRUCTIONS **
        You will be given a piece of text and you will need to the detemine if the text 
        contains a request to generate or create an image.

        Strictly follow the instructions below:

        If a user input contains a request to generate an image, return 'True'.
        else return 'False'

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

    input_data = [system_prompt, prompt]

    response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=input_data,
    max_tokens=8
    ).choices[0].message.content

    return True if response == 'True' else False