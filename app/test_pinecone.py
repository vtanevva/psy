from chat_embeddings import search_chat_memory

query = "i feel sad"
results = search_chat_memory(query)

print("Top matches for:", query)
for i, res in enumerate(results, 1):
    print(f"{i}. {res}")
