import os
from openai import OpenAI
from dotenv import load_dotenv
from embeddings import search_similar_chunks
from emotion_detection import detect_emotion, detect_suicidal_intent


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chat_with_gpt(user_message):
    # Run detectors first
    emotion, score = detect_emotion(user_message)
    suicide_risk = detect_suicidal_intent(user_message)

    # 🔒 Contextual response setup
    top_chunks = search_similar_chunks(user_message)
    context = "\n\n".join(top_chunks)

    # Add extra support if risk detected
    safety_note = ""
    if suicide_risk:
        safety_note = (
            "⚠️ It sounds like you're really struggling. You're not alone. "
            "Please consider talking to a real person. Here are some helplines:\n"
            "- International: https://findahelpline.com/\n"
            "- 113 Zelfmoordpreventie (NL): 0800-0113\n"
        )
    elif emotion in ["sadness", "fear"]:
        safety_note = "🧡 I hear you're feeling {}. I'm here for you.".format(emotion)

    # GPT call
    messages = [
        {"role": "system", "content": "You are a gentle, emotionally intelligent assistant."},
        {"role": "system", "content": f"Context:\n{context}"},
        {"role": "system", "content": f"Emotion Detected: {emotion}"},
        {"role": "user", "content": f"{user_message}\n\n{safety_note}"}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=150,
        temperature=0.7
    )

    return response.choices[0].message.content
