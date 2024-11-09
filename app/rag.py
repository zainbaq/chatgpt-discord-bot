import chromadb
from chromadb.config import Settings
from transformers import AutoTokenizer, AutoModel
import torch

class ConversationVectorStore:
    def __init__(self, base_collection_name="conversations"):
        self.base_collection_name = base_collection_name
        self.client = chromadb.Client()
    
    def insert_conversation_to_memory(self, interaction, conversation_collection="conversations"):

        conv_collection = self.chroma_client.get_or_create_collection(name=conversation_collection)

        vector = self.embed(interaction)
        
        conv_collection.upsert(
                documents=[interaction],
                embeddings=[vector.tolist()],
                # metadatas=[metadata]
            )


    def embed(self, text, model_name):
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
            query_embeddings = self.embed(query_text)
            return collection.query(query_embeddings, n_results=n_results)
        else:
            return collection.query(query_text, n_results=n_results)