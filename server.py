import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from flask import Flask, request, jsonify
from flask_cors import CORS

import uuid

from app.chatbot import chat_with_gpt
from app.memory import save_message
from app.chat_embeddings import save_chat_to_memory
from app.chat_embeddings import extract_facts_with_gpt


app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def index():
    print("Root path hit")
    return "Psychology chatbot backend is running!"


app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    print("Raw data:", data)

    user_message = data.get("message", "").strip()
    user_id = data.get("user_id", "anonymous").strip().lower() or "anonymous"
    session_id = data.get("session_id", f"{user_id}-{str(uuid.uuid4())[:8]}")  # ✅ NOW DEFINED SAFELY

    if not user_message:
        return jsonify({"reply": "No message received. Please enter something."}), 400

    try:
        # 💬 Get GPT reply
        reply, emotion, suicide_flag = chat_with_gpt(user_message, user_id=user_id, session_id=session_id, return_meta=True)
        print("Reply from GPT:", reply)

        # 💾 Save message to disk
        save_message(session_id, user_message, reply, emotion, suicide_flag)

        # 📌 Extract and store facts
        extracted_facts = extract_facts_with_gpt(user_message)
        for line in extracted_facts.split("\n"):
            if line.strip().lower() != "none":
                save_chat_to_memory(f"FACT: {line.strip('- ')}", session_id, user_id=user_id, emotion=emotion)

        return jsonify({"reply": reply})

    except Exception as e:
        print("GPT error:", e)
        return jsonify({"reply": "Something went wrong. Please try again."}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5555)
