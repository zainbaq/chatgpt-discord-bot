import chromadb  # ChromaDB library for vector database operations
from chromadb.config import Settings  # Settings for ChromaDB configuration
import hashlib  # For generating MD5 hashes
import uuid  # For generating UUIDs
import os  # For accessing environment variables
from openai import OpenAI  # OpenAI API client
from chromadb.errors import DuplicateIDError  # Error handling for duplicate IDs

# Note: Unused imports and code related to transformers and torch have been removed for clarity

def generate_consistent_guid(param1):
    """
    Generate a consistent GUID based on the input string.
    This ensures that the same input string always produces the same GUID.

    Args:
        param1 (str): The input string to generate the GUID from.

    Returns:
        str: A string representation of the UUID.
    """
    if param1 is None:
        return None
    else:
        # Compute MD5 hash of the input string
        md5_hash = hashlib.md5(param1.encode('utf-8')).digest()
        
        # Rearrange bytes to match SQL Server's UNIQUEIDENTIFIER format
        b = md5_hash
        # Data1: bytes 0-3, reversed
        data1 = b[3::-1]
        # Data2: bytes 4-5, reversed
        data2 = b[5:3:-1]
        # Data3: bytes 6-7, reversed
        data3 = b[7:5:-1]
        # Data4: bytes 8-15, as is
        data4 = b[8:]
        
        # Combine the rearranged bytes
        guid_bytes = data1 + data2 + data3 + data4
        # Create UUID from bytes
        guid = uuid.UUID(bytes=guid_bytes)
        # Return string representation of the UUID
        return str(guid)

class ConversationVectorStore:
    def __init__(self, base_collection_name="conversations"):
        """
        Initialize the ConversationVectorStore.

        Args:
            base_collection_name (str): The name of the base collection in ChromaDB.
        """
        self.base_collection_name = base_collection_name
        self.client = chromadb.Client()  # Initialize ChromaDB client
        # Get or create the conversation collection
        self.conv_collection = self.client.get_or_create_collection(name=base_collection_name)
      
    def insert_conversation_to_memory(self, interaction):
        """
        Insert a conversation or interaction into the vector store.

        Args:
            interaction (list): A list of interaction strings to be stored.
        """
        # Generate consistent GUIDs for each interaction
        ids = [generate_consistent_guid(x) for x in interaction]
        # Generate embeddings for each interaction
        vectors = [self.embed(x) for x in interaction]

        try:
            # Upsert (update or insert) the interactions into the collection
            self.conv_collection.upsert(
                ids=ids,
                documents=interaction,
                embeddings=vectors,
                # metadatas=[metadata]  # Metadata can be added if needed
            )
        except DuplicateIDError as e:
            print('[WARNING] Record already exists.')
            print(e)

    def embed(self, text, model_name="text-embedding-ada-002"):
        """
        Generate an embedding for the given text using OpenAI's embedding model.

        Args:
            text (str): The text to embed.
            model_name (str): The name of the embedding model to use.

        Returns:
            list: The embedding vector for the text.
        """
        # Initialize OpenAI client with API key
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        try:
            # Create embedding using OpenAI API
            response = client.embeddings.create(
                model=model_name,
                input=text,
                encoding_format="float"
            )
            # Return the embedding vector
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def query(self, collection_name, query_text, n_results=3, embed=True):
        """
        Query the vector store to retrieve similar documents.

        Args:
            collection_name (str): The name of the collection to query.
            query_text (str): The text query to search for.
            n_results (int): The number of results to return.
            embed (bool): Whether to embed the query_text before querying.

        Returns:
            dict: The query results from the collection.
        """
        # Retrieve the specified collection
        collection = self.client.get_collection(collection_name)
        if embed:
            # Embed the query text
            query_embedding = self.embed(query_text)
            if query_embedding is not None:
                # Query the collection using the embedding
                return collection.query(query_embedding, n_results=n_results)
            else:
                print("Failed to generate query embedding.")
                return {}
        else:
            # Query the collection using the raw text
            return collection.query(query_text, n_results=n_results)