import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# App setup
app = Flask(__name__, static_folder="my-chatbot/build", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Load .env variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client.chatbot_db
conversations = db.conversations

# Local imports
from app.chatbot import chat_with_gpt
from app.chat_embeddings import save_chat_to_memory, extract_facts_with_gpt

# ============ SAVE MESSAGE ============
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
            "$push": {"messages": {"$each": [message_pair, bot_response]}},
        },
        upsert=True
    )

# ============ CHAT ENDPOINT ============
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    user_id = data.get("user_id", "anonymous").strip().lower() or "anonymous"
    session_id = data.get("session_id", f"{user_id}-{str(uuid.uuid4())[:8]}")

    if not user_message:
        return jsonify({"reply": "No message received. Please enter something."}), 400

    try:
        session_memory = []
        chat_doc = conversations.find_one({"user_id": user_id, "session_id": session_id})
        if chat_doc and "messages" in chat_doc:
            for msg in chat_doc["messages"][-20:]:
                role = msg["role"]
                if role == "bot": role = "assistant"
                session_memory.append({"role": role, "content": msg["text"]})

        reply, emotion, suicide_flag = chat_with_gpt(
            user_message,
            user_id=user_id,
            session_id=session_id,
            return_meta=True,
            session_memory=session_memory
        )

        save_message(user_id, session_id, user_message, reply, emotion, suicide_flag)

        extracted_facts = extract_facts_with_gpt(user_message)
        for line in extracted_facts.split("\n"):
            if line.strip().lower() != "none":
                save_chat_to_memory(f"FACT: {line.strip('- ')}", session_id, user_id=user_id, emotion=emotion)

        return jsonify({"reply": reply})

    except Exception as e:
        print("GPT error:", e)
        return jsonify({"reply": "Something went wrong. Please try again."}), 500

# ============ SESSIONS ============
@app.route("/api/sessions-log", methods=["POST"])
def sessions_log():
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    sessions = conversations.find({"user_id": user_id})
    session_map = {s["session_id"]: s.get("session_name", "") for s in sessions}

    session_list = [{"session_id": sid, "name": name} for sid, name in session_map.items()]
    return jsonify({"sessions": session_list})

@app.route("/api/session_chat", methods=["POST"])
def session_chat():
    user_id = request.json.get("user_id")
    session_id = request.json.get("session_id")
    entry = conversations.find_one({"user_id": user_id, "session_id": session_id})
    return jsonify({"chat": entry.get("messages", []) if entry else []})

@app.route("/api/save-session-name", methods=["POST"])
def save_session_name():
    data = request.get_json()
    db.conversations.update_one(
        {"user_id": data["user_id"], "session_id": data["session_id"]},
        {"$set": {"session_name": data["name"]}},
        upsert=True
    )
    return jsonify({"status": "ok"})

@app.route("/api/test-mongo")
def test_mongo():
    conversations.insert_one({"msg": "Mongo is working!", "timestamp": datetime.utcnow()})
    return jsonify({"status": "success"})

# ============ SERVE FRONTEND ============
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

# ============ RUN LOCALLY ============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5555))  # Use Render's PORT or fallback
    app.run(host="0.0.0.0", port=port)
