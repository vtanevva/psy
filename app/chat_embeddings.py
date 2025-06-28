import os
import numpy as np
from uuid import uuid4
import openai 
from dotenv import load_dotenv
from tiktoken import get_encoding
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# init OpenAI and tokenizer
openai.api_key = os.getenv("OPENAI_API_KEY")
encoding = get_encoding("cl100k_base")

# Pinecone setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX_NAME")
pinecone_env = os.getenv("PINECONE_ENVIRONMENT")

# creating index if it doesn't exist
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=pinecone_env)
    )

index = pc.Index(index_name)

# what messages are worth embedding
def should_embed(text: str) -> bool:
    MIN_TOKENS = 10
    IGNORE_KEYWORDS = ["thank you", "hi", "ok", "sure", "bye"]
    if any(k in text.lower() for k in IGNORE_KEYWORDS):
        return False
    if len(text.split()) < 3:
        return False
    return True

# embedding using OpenAI
def embed_text(text):
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

# saving to Pinecone under user's namespace
def save_chat_to_memory(message_text, session_id, user_id="default", emotion="neutral"):
    if not should_embed(message_text):
        return

    embedding = embed_text(message_text)
    vector_id = f"{session_id}-{str(uuid4())[:6]}"

    index.upsert(
        vectors=[
            {
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "text": message_text,
                    "session_id": session_id,
                    "user_id": user_id,
                    "emotion": emotion
                }
            }
        ],
        namespace=user_id  # per-user memory space
    )

# search memory for similar messages (user specific)
def search_chat_memory(query, top_k=3, user_id="default"):
    embedding = embed_text(query)

    response = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=user_id  # ensures personalized memory
    )

    return [match["metadata"]["text"] for match in response.matches]


def get_user_facts(user_id, namespace=None):
    if namespace is None:
        namespace = user_id
    try:
        results = index.query(
            vector=[0.0] * 1536,  # dummy vector
            namespace=namespace,
            top_k=100,
            include_metadata=True
        )
        return [
            m['metadata']['text']
            for m in results['matches']
            if m['metadata'].get('text', '').startswith("FACT:")
        ]
    except Exception as e:
        print("❌ Error getting facts from Pinecone:", e)
        return []


def summarize_old_facts(context_text: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are summarizing facts about a user to help a psychology chatbot remember important details."
                },
                {
                    "role": "user",
                    "content": f"Summarize these known facts about the user:\n\n{context_text}"
                }
            ],
            max_tokens=150
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ Error in summarize_old_facts():", e)
        return ""



def extract_facts_with_gpt(user_input):
    """
    Extracts meaningful personal facts from user input using GPT.
    """
    try:
        prompt = f"""Extract any personal facts from the following sentence. 
Respond only with bullet points or 'None' if nothing is extractable.

Sentence: "{user_input}"
"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You extract factual statements from user inputs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("❌ Error extracting facts:", e)
        return "None"
