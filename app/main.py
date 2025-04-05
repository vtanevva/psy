import os
import uuid
from chatbot import chat_with_gpt
from memory import save_message
from chat_embeddings import save_chat_to_memory

# Optional: fix OpenMP error if needed (Intel + Torch conflict)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Generate a unique session ID for this run
session_id = str(uuid.uuid4())[:8]  # e.g., "7c4a2f"

print(f"🧠 New Session Started (ID: {session_id})")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() in ['exit', 'quit']:
        print("👋 Ending session.")
        break

    try:
        reply, emotion, suicide_flag = chat_with_gpt(user_input, return_meta=True)
        print("Bot:", reply)

        # Save both log and memory embeddings
        save_message(session_id, user_input, reply, emotion, suicide_flag)
        save_chat_to_memory(f"User: {user_input}", session_id)
        save_chat_to_memory(f"Bot: {reply}", session_id)

    except Exception as e:
        print("❌ An error occurred:", e)
