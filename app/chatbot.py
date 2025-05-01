import os
from dotenv import load_dotenv
import openai
from .emotion_detection import detect_emotion, detect_suicidal_intent
from .embeddings import search_similar_chunks
from .chat_embeddings import search_chat_memory


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def chat_with_gpt(user_message, return_meta=False):
    emotion, _ = detect_emotion(user_message)
    suicide_flag = detect_suicidal_intent(user_message)

    chat_memory_chunks = search_chat_memory(user_message)
    memory_context = "\n\n".join(chat_memory_chunks)

    top_chunks = search_similar_chunks(user_message)
    data_context = "\n\n".join(top_chunks)

    # safety_note before condition
    safety_note = ""

    # emotional support if the message has enough substance
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

    messages = [
        {"role": "system", "content": "You are a therapist, you initiate conversation with the user aiming to build trust, encourage self-reflection, and gently guide them to explore their thoughts and emotions at their own pace."},
        {"role": "system", "content": f"User memory:\n{memory_context}"},
        {"role": "system", "content": f"Relevant psychological info:\n{data_context}"},
        {"role": "user", "content": f"{user_message}\n\n{safety_note}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=80,
        temperature=0.7
    )

    reply = response.choices[0].message.content.strip()

    if return_meta:
        return reply, emotion, suicide_flag
    return reply
