import chromadb
from chromadb.config import Settings
from transformers import AutoTokenizer, AutoModel
import torch
import hashlib
import uuid

def generate_consistent_guid(param1):
    if param1 is None:
        return None
    else:
        # Compute MD5 hash of param1 as bytes
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
        self.base_collection_name = base_collection_name
        self.client = chromadb.Client()
        self.conv_collection = self.client.get_or_create_collection(name=base_collection_name)
      
    def insert_conversation_to_memory(self, interaction):

        ids = [generate_consistent_guid(x) for x in interaction]
        vector = [self.embed(x)[0].tolist()[0] for x in interaction]

        self.conv_collection.upsert(
                ids=ids,
                documents=interaction,
                embeddings=vector,
                # metadatas=[metadata]
            )


    def embed(self, text, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)

        if type(text) == str:
            text = [text]
        
        embeddings = []
        for string in text:
            tokens = tokenizer(string, return_tensors='pt')

            with torch.no_grad():
                output = model(**tokens)
            
            last_hidden_state = output.last_hidden_state
            contextual_embeddings = last_hidden_state.mean(dim=1)
            embeddings.append(contextual_embeddings)

        return embeddings
    
    def query(self, collection_name, query_text, n_results=3, embed=True):
        collection = self.client.get_collection(collection_name)
        if embed:
            query_embeddings = self.embed(query_text)[0].tolist()
            return collection.query(query_embeddings, n_results=n_results)
        else:
            return collection.query(query_text, n_results=n_results)