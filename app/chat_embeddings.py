import os
import numpy as np
from uuid import uuid4

import openai
from dotenv import load_dotenv
from tiktoken import get_encoding
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# --- OpenAI setup -----------------------------------------------------------
openai.api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
encoding = get_encoding("cl100k_base")

# --- Pinecone env vars (strip to avoid stray whitespace/newlines) ----------
PINECONE_API_KEY = (os.getenv("PINECONE_API_KEY") or "").strip()
# Accept either var name
PINECONE_ENV = (
    os.getenv("PINECONE_ENV") or
    os.getenv("PINECONE_ENVIRONMENT") or
    "us-east-1"              # sensible default; change if needed
).strip()

INDEX_NAME = (os.getenv("PINECONE_INDEX_NAME") or "chatbot-facts").strip()

if not PINECONE_API_KEY:
    raise RuntimeError("PINECONE_API_KEY is missing.")

# --- Pinecone client -------------------------------------------------------
pc = Pinecone(api_key=PINECONE_API_KEY)

# List existing indexes (SDK v5 returns list of dicts)
try:
    existing_indexes = [ix["name"] for ix in pc.list_indexes()]
except Exception as e:
    print(f"❌ Pinecone list_indexes() failed: {e}", flush=True)
    existing_indexes = []

# Create index if needed
if INDEX_NAME not in existing_indexes:
    print(f"[INIT] Creating Pinecone index '{INDEX_NAME}' in region '{PINECONE_ENV}'...", flush=True)
    try:
        pc.create_index(
            name=INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV)
        )
    except Exception as e:
        print(f"❌ Error creating Pinecone index: {e}", flush=True)

# Connect to index
index = pc.Index(INDEX_NAME)
print(f"[INIT] Pinecone ready. Index='{INDEX_NAME}'", flush=True)


# ---------------------------------------------------------------------------
# Utility: filter what to embed
# ---------------------------------------------------------------------------
def should_embed(text: str) -> bool:
    IGNORE_KEYWORDS = ("thank you", "hi", "ok", "sure", "bye")
    if any(k in text.lower() for k in IGNORE_KEYWORDS):
        return False
    if len(text.split()) < 3:
        return False
    return True


# ---------------------------------------------------------------------------
# Embedding (OpenAI)  -- NOTE: model upgrade recommended later
# ---------------------------------------------------------------------------
def embed_text(text: str):
    resp = openai.Embedding.create(
        model="text-embedding-ada-002",  # consider `text-embedding-3-small` soon
        input=text,
    )
    return resp.data[0].embedding


# ---------------------------------------------------------------------------
# Save vector to Pinecone (user namespace)
# ---------------------------------------------------------------------------
def save_chat_to_memory(message_text, session_id, user_id="default", emotion="neutral"):
    if not should_embed(message_text):
        return

    emb = embed_text(message_text)
    vector_id = f"{session_id}-{str(uuid4())[:6]}"

    try:
        index.upsert(
            vectors=[
                {
                    "id": vector_id,
                    "values": emb,
                    "metadata": {
                        "text": message_text,
                        "session_id": session_id,
                        "user_id": user_id,
                        "emotion": emotion,
                    },
                }
            ],
            namespace=user_id,
        )
    except Exception as e:
        print(f"❌ Pinecone upsert error: {e}", flush=True)


# ---------------------------------------------------------------------------
# Semantic search in user namespace
# ---------------------------------------------------------------------------
def search_chat_memory(query, top_k=3, user_id="default"):
    emb = embed_text(query)
    try:
        resp = index.query(
            namespace=user_id,
            vector=emb,
            top_k=top_k,
            include_metadata=True,
        )
    except Exception as e:
        print(f"❌ Pinecone query error: {e}", flush=True)
        return []

    matches = getattr(resp, "matches", None) or resp.get("matches", [])
    out = []
    for m in matches:
        md = getattr(m, "metadata", None) or m.get("metadata", {})
        txt = md.get("text")
        if txt:
            out.append(txt)
    return out


# ---------------------------------------------------------------------------
# Fetch stored user "FACT:" items
# ---------------------------------------------------------------------------
def get_user_facts(user_id, namespace=None):
    ns = namespace or user_id

    # Quick wide search: query with a random vector & large top_k
    # (Pinecone doesn't have "list all vectors" by namespace)
    try:
        # Query with zero vector; with cosine metric, score=0 but we just want metadata
        zero_vec = [0.0] * 1536
        resp = index.query(
            namespace=ns,
            vector=zero_vec,
            top_k=200,
            include_metadata=True,
        )
    except Exception as e:
        print(f"❌ Error getting facts from Pinecone: {e}", flush=True)
        return []

    matches = getattr(resp, "matches", None) or resp.get("matches", [])
    facts = []
    for m in matches:
        md = getattr(m, "metadata", None) or m.get("metadata", {})
        txt = md.get("text", "")
        if txt.startswith("FACT:"):
            facts.append(txt)
    return facts


# ---------------------------------------------------------------------------
# Summarize a batch of known facts
# ---------------------------------------------------------------------------
def summarize_old_facts(context_text: str) -> str:
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are summarizing facts about a user to help a psychology chatbot "
                        "remember important details."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Summarize these known facts about the user:\n\n{context_text}",
                },
            ],
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Error in summarize_old_facts():", e, flush=True)
        return ""


# ---------------------------------------------------------------------------
# Extract personal facts from a user message
# ---------------------------------------------------------------------------
def extract_facts_with_gpt(user_input: str) -> str:
    prompt = f"""
Extract factual personal statements from the following user input. 
Examples: name, age, location, job, preferences, relationships, hobbies, beliefs, or other memorable details.
Respond one per line, each starting with 'FACT:'.
Return 'None' if there's nothing to store.

User input: "{user_input}"
"""
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a fact extractor for a psychology chatbot. You help save user facts to memory.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
            temperature=0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Error extracting facts:", e, flush=True)
        return "None"
