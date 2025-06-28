import os
from dotenv import load_dotenv
import openai

from .emotion_detection import detect_emotion, detect_suicidal_intent
from .embeddings import search_similar_chunks
from .chat_embeddings import get_user_facts
from .chat_embeddings import summarize_old_facts


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def chat_with_gpt(user_message, user_id="default",session_id=None, return_meta=False):
    # 🔍 Emotion + Crisis Detection
    emotion, _ = detect_emotion(user_message)
    suicide_flag = detect_suicidal_intent(user_message)

    # 🧠 Get personalized FACT memory from Pinecone
    fact_list = get_user_facts(user_id=user_id)
    fact_memory = "\n".join(f"- {fact}" for fact in fact_list) if fact_list else "No known facts."
    fact_summary = summarize_old_facts(user_id=user_id, exclude_session_id=session_id)

    # 📚 Get related RAG context (optional background info)
    top_chunks = search_similar_chunks(user_message)
    data_context = "\n\n".join(top_chunks) if top_chunks else "No relevant context found."

    # ⚠️ Emotional warning messages if needed
    safety_note = ""
    if len(user_message.split()) >= 3:
        if suicide_flag:
            safety_note = (
                "⚠️ It sounds like you're really struggling. You're not alone.\n"
                "Please consider talking to someone:\n"
                "- https://findahelpline.com/\n"
                "- 113 Zelfmoordpreventie (NL): 0800-0113"
            )
        elif emotion in ["sadness", "fear"]:
            safety_note = f"I hear you're feeling {emotion}. I'm here for you."

    # 🧠 Compose full prompt with memory and context
    messages = [
        {
            "role": "system",
            "content": (
                "You are a compassionate psychology chatbot. The user may have talked to you before.\n"
                f"Here are some personal facts you've learned about them:\n{fact_memory}\n"
                f"Here is what you've learned about the user from past conversations:\n{fact_summary}\n"
                "Use these facts to personalize your replies when relevant."
            )
        },
        {
            "role": "system",
            "content": f"External psychological background context:\n{data_context}"
        },
        {
            "role": "user",
            "content": f"{user_message}\n\n{safety_note}"
        }
    ]
        # 🧠 DEBUGGING: See what GPT gets
    print("\n--- FACT MEMORY ---")
    print(fact_memory)

    print("\n--- FULL PROMPT MESSAGES ---")
    for msg in messages:
        print(f"[{msg['role'].upper()}] {msg['content']}\n")

    # 🤖 Get GPT response
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=150,
        temperature=0.7
    )

    reply = response.choices[0].message.content.strip()

    if return_meta:
        return reply, emotion, suicide_flag
    return reply
