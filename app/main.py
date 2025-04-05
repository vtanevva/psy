import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from chatbot import chat_with_gpt

while True:
    user_input = input("You: ")
    if user_input.lower() in ['exit', 'quit']:
        break
    reply = chat_with_gpt(user_input)
    print("Bot:", reply)
