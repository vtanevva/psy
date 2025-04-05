import faiss
import os
import pickle
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from tiktoken import get_encoding

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

encoding = get_encoding("cl100k_base")
MEMORY_INDEX_PATH = "chat_memory_index.faiss"
MEMORY_CHUNKS_PATH = "chat_chunks.pkl"

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

def save_chat_to_memory(message_text, session_id):
    if not should_embed(message_text):
        return  # Skip short or irrelevant text

    embedding = embed_text(message_text)

    if os.path.exists(MEMORY_INDEX_PATH):
        index = faiss.read_index(MEMORY_INDEX_PATH)
        with open(MEMORY_CHUNKS_PATH, "rb") as f:
            chunks = pickle.load(f)
    else:
        index = faiss.IndexFlatL2(1536)  # For text-embedding-3-small
        chunks = []

    chunks.append({"session": session_id, "text": message_text})
    index.add(np.array([embedding], dtype='float32'))

    faiss.write_index(index, MEMORY_INDEX_PATH)
    with open(MEMORY_CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)

def search_chat_memory(query, top_k=3):
    if not os.path.exists(MEMORY_INDEX_PATH):
        return []

    query_embedding = embed_text(query)
    index = faiss.read_index(MEMORY_INDEX_PATH)

    with open(MEMORY_CHUNKS_PATH, "rb") as f:
        chunks = pickle.load(f)

    D, I = index.search(np.array([query_embedding], dtype='float32'), top_k)
    results = [chunks[i]["text"] for i in I[0]]
    return results
