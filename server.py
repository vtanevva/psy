import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from flask import Flask, request, jsonify
from flask_cors import CORS

from app.chatbot import chat_with_gpt

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def index():
    print("Root path hit")
    return "Psychology chatbot backend is running!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    print("Raw data:", data)

    user_message = data.get("message", "")
    print("Received user message:", user_message)

    if not user_message.strip():
        return jsonify({"reply": "No message received. Please enter something."}), 400

    try:
        reply, _, _ = chat_with_gpt(user_message, return_meta=True)
        print("Reply from GPT:", reply)
        return jsonify({"reply": reply})
    except Exception as e:
        print("GPT error:", e)
        return jsonify({"reply": "Something went wrong. Please try again."})

if __name__ == "__main__":
    app.run(debug=True, port=5555)
