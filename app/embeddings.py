import os
import openai
import faiss
import pickle
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from typing import List
from tiktoken import get_encoding

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
encoding = get_encoding("cl100k_base")

def split_text(text: str, max_tokens=300) -> List[str]:
    words = text.split()
    chunks = []
    chunk = []
    token_count = 0

    for word in words:
        token_count += len(encoding.encode(word))
        chunk.append(word)
        if token_count >= max_tokens:
            chunks.append(" ".join(chunk))
            chunk = []
            token_count = 0
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks

def embed_text_chunks(chunks: List[str]):
    response = client.embeddings.create(
        input=chunks,
        model="text-embedding-3-small"
    )
    return [record.embedding for record in response.data]

def build_vector_store(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = split_text(text)
    embeddings = embed_text_chunks(chunks)

    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings).astype("float32"))

    with open("rag_chunks.pkl", "wb") as f:
        pickle.dump(chunks, f)
    faiss.write_index(index, "rag_index.faiss")

    print("✅ Vector store built and saved.")

# ✅ These must be OUTSIDE the __main__ block to allow importing
def load_vector_store():
    index = faiss.read_index("rag_index.faiss")
    with open("rag_chunks.pkl", "rb") as f:
        chunks = pickle.load(f)
    return index, chunks

def search_similar_chunks(user_query: str, top_k=3):
    index, chunks = load_vector_store()
    
    query_embedding = client.embeddings.create(
        input=[user_query],
        model="text-embedding-3-small"
    ).data[0].embedding

    D, I = index.search(np.array([query_embedding], dtype='float32'), top_k)
    results = [chunks[i] for i in I[0]]
    return results

# Optional: allow manual rebuild from CLI
if __name__ == "__main__":
    build_vector_store("data/psychology_guide.txt")
