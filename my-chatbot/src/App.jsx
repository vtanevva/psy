import { useState } from "react";

function App() {
  const [input, setInput] = useState("");
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState("");
  const [entered, setEntered] = useState(false);
  const [sessionId, setSessionId] = useState("");

  const generateSessionId = (id) => `${id}-${crypto.randomUUID().slice(0, 8)}`;

  const handleStart = (e) => {
    e.preventDefault();
    if (userId.trim()) {
      const cleanUser = userId.toLowerCase().trim();
      setUserId(cleanUser);
      setSessionId(generateSessionId(cleanUser));
      setEntered(true);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", text: input };
    setChat((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:5555/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          user_id: userId,
          session_id: sessionId,
        }),
      });

      const data = await res.json();
      const botMessage = { role: "bot", text: data.reply };
      setChat((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error("❌ Error talking to backend:", err);
    }

    setLoading(false);
  };

  const handleNewSession = () => {
    setSessionId(generateSessionId(userId));
    setChat([]);
  };

  if (!entered) {
    return (
      <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-6">
        <form onSubmit={handleStart} className="space-y-4 text-center">
          <h1 className="text-2xl font-bold">🧠 Welcome to the Psychology Chatbot</h1>
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter your name"
            className="border border-gray-400 rounded px-4 py-2"
            required
          />
          <button
            type="submit"
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Start Chat
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-6">
      <h1 className="text-2xl font-bold mb-4">🧠 Psychology Chatbot</h1>

      <div className="w-full max-w-md bg-white rounded shadow p-4 flex-1 flex flex-col">
        <div className="text-sm text-gray-600 mb-2">
          <strong>User:</strong> {userId} &nbsp; | &nbsp;
          <strong>Session:</strong> {sessionId}
        </div>

        <div className="flex-1 overflow-y-auto mb-4 space-y-2">
          {chat.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`p-2 rounded-lg max-w-xs ${
                  msg.role === "user"
                    ? "bg-blue-100 text-right"
                    : "bg-gray-200 text-left"
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          {loading && <div className="text-sm text-gray-500">Typing...</div>}
        </div>

        <div className="flex gap-2 mb-2">
          <input
            className="border p-2 rounded flex-1"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button
            className="bg-blue-500 text-white px-4 py-2 rounded"
            onClick={handleSend}
            disabled={loading}
          >
            Send
          </button>
        </div>

        <button
          onClick={handleNewSession}
          className="text-sm text-blue-500 underline"
        >
          🔁 Start New Chat
        </button>
      </div>
    </div>
  );
}

export default App;
