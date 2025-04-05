import json
import os
from datetime import datetime

HISTORY_DIR = "chat_history"

# Make sure directory exists
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_history_path(session_id):
    return os.path.join(HISTORY_DIR, f"{session_id}.json")

def save_message(session_id, user_message, bot_reply, emotion=None, suicide_flag=False):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user_message,
        "bot": bot_reply,
        "emotion": emotion,
        "suicide_flag": suicide_flag
    }

    path = get_history_path(session_id)

    history = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)

    history.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def load_history(session_id):
    path = get_history_path(session_id)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
