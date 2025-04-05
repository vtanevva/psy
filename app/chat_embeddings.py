import os
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from tiktoken import get_encoding
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# Init OpenAI and tokenizer
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
encoding = get_encoding("cl100k_base")

# Pinecone setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX_NAME")

# Create index if it doesn't exist
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",  # or "euclidean" depending on your setup
        spec=ServerlessSpec(
            cloud="aws",
            region=os.getenv("PINECONE_ENVIRONMENT")  # us-east-1 etc.
        )
    )

index = pc.Index(index_name)

def should_embed(text: str) -> bool:
    MIN_TOKENS = 10
    IGNORE_KEYWORDS = ["thank you", "hi", "ok", "sure", "bye"]
    if any(k in text.lower() for k in IGNORE_KEYWORDS):
        return False
    if len(text.split()) < 3:
        return False
    return True

def embed_text(text):
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def save_chat_to_memory(message_text, session_id, user_id):
    if not should_embed(message_text):
        return

    embedding = embed_text(message_text)
    vector_id = f"{session_id}-{np.random.randint(1_000_000)}"

    index.upsert(vectors=[
        {
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "session_id": session_id,
                "user_id": user_id,
                "text": message_text
            }
        }
    ])

def search_chat_memory(query, top_k=3, user_id=None):
    embedding = embed_text(query)

    filter_by_user = {"user_id": user_id} if user_id else None

    response = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_by_user
    )

    return [match["metadata"]["text"] for match in response.matches]
