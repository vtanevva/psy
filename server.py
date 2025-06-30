import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from flask import Flask, request, jsonify
from flask_cors import CORS

import uuid

from app.chatbot import chat_with_gpt
from app.memory import save_message
from app.chat_embeddings import save_chat_to_memory
from app.chat_embeddings import extract_facts_with_gpt
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client.chatbot_db
conversations = db.conversations

from datetime import datetime

def save_message(user_id, session_id, user_message, bot_reply, emotion=None, suicide_flag=False):
    message_pair = {
        "timestamp": datetime.utcnow().isoformat(),
        "role": "user",
        "text": user_message,
        "emotion": emotion,
        "suicide_flag": suicide_flag,
    }

    bot_response = {
        "timestamp": datetime.utcnow().isoformat(),
        "role": "bot",
        "text": bot_reply,
    }

    conversations.update_one(
        {"user_id": user_id, "session_id": session_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.utcnow(),
            },
            "$push": {
                "messages": {"$each": [message_pair, bot_response]},
            },
        },
        upsert=True
    )



@app.route("/", methods=["GET"])
def index():
    print("Root path hit")
    return "Psychology chatbot backend is running!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    print("Raw data:", data)

    user_message = data.get("message", "").strip()
    user_id = data.get("user_id", "anonymous").strip().lower() or "anonymous"
    session_id = data.get("session_id", f"{user_id}-{str(uuid.uuid4())[:8]}")

    if not user_message:
        return jsonify({"reply": "No message received. Please enter something."}), 400

    try:
        session_memory = []
        chat_doc = conversations.find_one({"user_id": user_id, "session_id": session_id})
        if chat_doc and "messages" in chat_doc:
            last_messages = chat_doc["messages"][-20:]  # last 10 exchanges
            for msg in last_messages:
                role = msg["role"]
                if role == "bot":
                    role = "assistant"  # ✅ Fix role for GPT
                session_memory.append({
                    "role": role,
                    "content": msg["text"]
                })


        # 💬 Generate GPT reply (pass memory)
        reply, emotion, suicide_flag = chat_with_gpt(
            user_message,
            user_id=user_id,
            session_id=session_id,
            return_meta=True,
            session_memory=session_memory
        )

        print("Reply from GPT:", reply)

        # 💾 Save full conversation to MongoDB
        save_message(user_id, session_id, user_message, reply, emotion, suicide_flag)

        # 📌 Extract facts (optional) and save to Pinecone
        extracted_facts = extract_facts_with_gpt(user_message)
        for line in extracted_facts.split("\n"):
            if line.strip().lower() != "none":
                save_chat_to_memory(
                    f"FACT: {line.strip('- ')}",
                    session_id,
                    user_id=user_id,
                    emotion=emotion
                )

        return jsonify({"reply": reply})

    except Exception as e:
        print("GPT error:", e)
        return jsonify({"reply": "Something went wrong. Please try again."}), 500


@app.route("/sessions-log", methods=["GET", "POST"])
def get_sessions():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200  # Preflight check success

    data = request.get_json()
    user_id = data.get("user_id")

    sessions = conversations.find({"user_id": user_id}, {"session_id": 1, "_id": 0})
    session_list = [s["session_id"] for s in sessions]
    return jsonify({"sessions": session_list})

@app.route("/sessions-log", methods=["GET"])
def reject_sessions_get():
    return jsonify({"error": "GET not allowed. Use POST with JSON."}), 405


@app.route("/session_chat", methods=["POST"])
def session_chat():
    user_id = request.json.get("user_id")
    session_id = request.json.get("session_id")
    entry = conversations.find_one({"user_id": user_id, "session_id": session_id})
    return jsonify({"chat": entry.get("messages", []) if entry else []})

@app.route("/test-mongo")
def test_mongo():
    conversations.insert_one({"msg": "Mongo is working!", "timestamp": datetime.utcnow()})
    return jsonify({"status": "success"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5555))  # default only for local
    app.run(host="0.0.0.0", port=port)