import os
from dotenv import load_dotenv
from openai import OpenAI
from emotion_detection import detect_emotion, detect_suicidal_intent
from embeddings import search_similar_chunks
from chat_embeddings import search_chat_memory

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chat_with_gpt(user_message, return_meta=False):
    # 🔍 1. Detect emotion + suicide risk
    emotion, _ = detect_emotion(user_message)
    suicide_flag = detect_suicidal_intent(user_message)

    # 🧠 2. Retrieve memory and context
    chat_memory_chunks = search_chat_memory(user_message)
    memory_context = "\n\n".join(chat_memory_chunks)

    top_chunks = search_similar_chunks(user_message)
    data_context = "\n\n".join(top_chunks)

    # 🛟 3. Add safety and empathy messages
    safety_note = ""
    if suicide_flag:
        safety_note = (
            "⚠️ It sounds like you're really struggling. You're not alone.\n"
            "Please consider talking to someone:\n"
            "- https://findahelpline.com/\n"
            "- 113 Zelfmoordpreventie (NL): 0800-0113"
        )
    elif emotion in ["sadness", "fear"]:
        safety_note = f"🧡 I hear you're feeling {emotion}. I'm here for you."

    # 💬 4. Construct messages
    messages = [
        {"role": "system", "content": "You are a gentle psychological assistant. Use context and memory to help the user calmly."},
        {"role": "system", "content": f"User memory:\n{memory_context}"},
        {"role": "system", "content": f"Relevant psychological info:\n{data_context}"},
        {"role": "user", "content": f"{user_message}\n\n{safety_note}"}
    ]

    # 🤖 5. Get GPT response
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=50,
        temperature=0.7
    )

    reply = response.choices[0].message.content.strip()

    # 🔁 6. Return result + metadata
    if return_meta:
        return reply, emotion, suicide_flag
    return reply
