from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def index():
    print("📥 Root hit")
    return "Hello from Flask!"

@app.route("/chat", methods=["POST"])
def chat():
    print("✅ Chat route was hit!")
    return jsonify({"reply": "Server is alive 🚀"})

if __name__ == "__main__":
    app.run(debug=True, port=5050)

