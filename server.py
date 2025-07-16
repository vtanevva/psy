import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import uuid
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------
app = Flask(__name__, static_folder="my-chatbot/build", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ------------------------------------------------------------------------------
# Config / DB
# ------------------------------------------------------------------------------
# Load .env variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable not set.")

client = MongoClient(MONGO_URI)

# Try to honor DB from URI; fallback
try:
    db = client.get_database()
except Exception:
    db = client["chatbot_db"]

conversations = db["conversations"]

print(f"[INIT] Mongo connected. DB={db.name}", flush=True)

# ------------------------------------------------------------------------------
# Local imports (your modules)
# ------------------------------------------------------------------------------
from app.chatbot import chat_with_gpt
from app.chat_embeddings import save_chat_to_memory, extract_facts_with_gpt


# ------------------------------------------------------------------------------
# Save message pair to Mongo
# ------------------------------------------------------------------------------
def save_message(user_id, session_id, user_message, bot_reply, emotion=None, suicide_flag=False):
    if conversations is None:
        return  # fail silently if DB not configured

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
        upsert=True,
    )


# ------------------------------------------------------------------------------
# /api/chat
# ------------------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()
    user_id = (data.get("user_id") or "anonymous").strip().lower() or "anonymous"
    session_id = data.get("session_id") or f"{user_id}-{str(uuid.uuid4())[:8]}"

    if not user_message:
        return jsonify({"reply": "No message received. Please enter something."}), 400

    try:
        # Pull recent context
        session_memory = []
        if conversations is not None:
            chat_doc = conversations.find_one({"user_id": user_id, "session_id": session_id})
            if chat_doc and "messages" in chat_doc:
                for msg in chat_doc["messages"][-20:]:
                    role = msg["role"]
                    if role == "bot":
                        role = "assistant"
                    session_memory.append({"role": role, "content": msg["text"]})

        # Call your model
        reply, emotion, suicide_flag = chat_with_gpt(
            user_message,
            user_id=user_id,
            session_id=session_id,
            return_meta=True,
            session_memory=session_memory,
        )

        # Persist
        save_message(user_id, session_id, user_message, reply, emotion, suicide_flag)

        # Extract & store facts
        extracted_facts = extract_facts_with_gpt(user_message)
        for line in extracted_facts.split("\n"):
            cleaned = line.strip()
            if cleaned and cleaned.lower() != "none":
                save_chat_to_memory(f"FACT: {cleaned.lstrip('- ').strip()}", session_id,
                                    user_id=user_id, emotion=emotion)

        return jsonify({"reply": reply})

    except Exception as e:
        print("GPT error:", e, flush=True)
        return jsonify({"reply": "Something went wrong. Please try again."}), 500


# ------------------------------------------------------------------------------
# /api/sessions-log
# ------------------------------------------------------------------------------
@app.route("/api/sessions-log", methods=["POST"])
def sessions_log():
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    if conversations is None:
        return jsonify({"sessions": []})

    sessions = conversations.find({"user_id": user_id})
    session_map = {s["session_id"]: s.get("session_name", "") for s in sessions}
    session_list = [{"session_id": sid, "name": name} for sid, name in session_map.items()]
    return jsonify({"sessions": session_list})


# ------------------------------------------------------------------------------
# /api/session_chat
# ------------------------------------------------------------------------------
@app.route("/api/session_chat", methods=["POST"])
def session_chat():
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("user_id")
    session_id = data.get("session_id")

    if conversations is None:
        return jsonify({"chat": []})

    entry = conversations.find_one({"user_id": user_id, "session_id": session_id})
    return jsonify({"chat": entry.get("messages", []) if entry else []})


# ------------------------------------------------------------------------------
# /api/save-session-name
# ------------------------------------------------------------------------------
@app.route("/api/save-session-name", methods=["POST"])
def save_session_name():
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("user_id")
    session_id = data.get("session_id")
    name = data.get("name", "")

    if conversations is not None:
        db.conversations.update_one(
            {"user_id": user_id, "session_id": session_id},
            {"$set": {"session_name": name}},
            upsert=True,
        )

    return jsonify({"status": "ok"})


# ------------------------------------------------------------------------------
# /api/test-mongo
# ------------------------------------------------------------------------------
@app.route("/api/test-mongo")
def test_mongo():
    if conversations is not None:
        conversations.insert_one({"msg": "Mongo is working!", "timestamp": datetime.utcnow()})
    return jsonify({"status": "success"})


# ------------------------------------------------------------------------------
# Serve built React frontend
# ------------------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    full_path = os.path.join(app.static_folder, path)
    if path != "" and os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ------------------------------------------------------------------------------
# Local dev (not used in Gunicorn container runtime)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    raw_port = os.environ.get("PORT", "5555")
    try:
        port = int(raw_port)
    except ValueError:
        print(f"[WARN] Invalid PORT value {raw_port!r}; falling back to 5555", flush=True)
        port = 5555

    # Production-safe run (no reloader, no debug)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
