"use client";
import { useState, useEffect, useRef } from "react";
import VoiceChat from "./pages/VoiceChat";

const BASE_URL = import.meta.env.MODE === "development"
  ? "http://192.168.0.102:5555"
  : "https://psy-6vvf.onrender.com";

function App() {
  const [input, setInput] = useState("");
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState("");
  const [entered, setEntered] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [useVoice, setUseVoice] = useState(false);

  const generateSessionId = (id) => `${id}-${crypto.randomUUID().slice(0, 8)}`;
  const chatContainerRef = useRef(null);

  useEffect(() => {
    chatContainerRef.current?.scrollTo({
      top: chatContainerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [chat]);

  const fetchSessions = async (id = userId) => {
    try {
      const res = await fetch(`${BASE_URL}/session_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: id }),
      });
      const data = await res.json();
      console.log("✅ Sessions fetched:", data.sessions);
      setSessions(data.sessions || []);
    } catch (err) {
      console.error("❌ Failed to fetch sessions:", err);
    }
  };

  const handleStart = async (e) => {
    e.preventDefault();
    if (userId.trim()) {
      const cleanUser = userId.toLowerCase().trim();
      setUserId(cleanUser);
      const newSession = generateSessionId(cleanUser);
      setSessionId(newSession);
      setEntered(true);
      setTimeout(() => {
        fetchSessions(cleanUser);
      }, 200);
    }
  };

const handleSend = async () => {
  if (!input.trim()) return;

  const userMessage = { role: "user", text: input };
  setChat((prev) => [...prev, userMessage]);
  setInput("");
  setLoading(true);

  try {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: input,
        user_id: userId,
        session_id: sessionId,
      }),
    });

    const data = await res.json();
    const botMessage = { role: "assistant", text: data.reply };
    setChat((prev) => [...prev, botMessage]);
  } catch (err) {
    console.error("❌ Error talking to backend:", err);
  }

  setLoading(false);
};


  const handleNewSession = () => {
    const newSessionId = generateSessionId(userId);
    setSessionId(newSessionId);
    setChat([]);
    setSelectedSession(null);
    setTimeout(() => {
      fetchSessions();
    }, 200);
  };

  const handleSessionSelect = async (e) => {
    const selected = e.target.value;
    setSelectedSession(selected);
    setSessionId(selected);
    console.log("📦 Selected session:", selected);
    try {
      const res = await fetch(`${BASE_URL}/session_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, session_id: selected }),
      });
      const data = await res.json();
      console.log("💬 Loaded chat:", data.chat);
      setChat(data.chat || []);
    } catch (err) {
      console.error("Error loading chat:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex flex-col items-center p-6 relative overflow-x-hidden">
      {!entered ? (
        <form onSubmit={handleStart} className="text-center space-y-6 mt-32">
          <img
            src="/robot-emoji.png"
            alt="Chatbot Logo"
            className="max-w-full h-auto mb-4"
          />
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter your name"
            className="px-4 py-2 rounded-lg text-center text-white bg-white/10 border border-white/30 placeholder-white/60 focus:outline-none"
            required
          />
          <br />
          <button
            type="submit"
            className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700"
          >
            Start Chat
          </button>
        </form>
      ) : useVoice ? (
        <VoiceChat userId={userId} sessionId={sessionId} setUseVoice={setUseVoice} />
      ) : (
        <div className="w-full max-w-xl flex flex-col bg-white/10 backdrop-blur-lg p-6 rounded-3xl shadow-lg border border-white/20 mt-10">
          <div className="flex justify-between items-center mb-4">
            <div className="text-white/80 text-sm">
              <span className="mr-4 font-semibold">👤 {userId}</span>
              <span className="text-xs">Session: {sessionId.slice(-8)}</span>
            </div>
            <button
              onClick={() => setUseVoice(!useVoice)}
              className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-4 py-2 rounded-lg text-sm hover:opacity-90"
            >
              {useVoice ? "💬 Switch to Text" : "🎙️ Switch to Voice"}
            </button>
          </div>

          <div className="mb-3">
            <label className="text-white/70 text-sm">Choose Session:</label>
            <select
              className="ml-2 bg-white/20 text-white p-1 rounded text-sm"
              value={selectedSession || ""}
              onChange={handleSessionSelect}
            >
              <option value="">-- select --</option>
              {sessions.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div
            ref={chatContainerRef}
            className="overflow-y-auto space-y-4 px-2 mb-4"
            style={{
              height: "400px",
              scrollBehavior: "smooth",
            }}
          >
            {chat.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`px-4 py-2 rounded-lg max-w-xs text-sm shadow-lg ${
                    msg.role === "user"
                      ? "bg-blue-500 text-white rounded-br-none"
                      : "bg-white/90 text-gray-800 rounded-bl-none"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && <div className="text-white text-sm">Typing...</div>}
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              className="flex-1 px-4 py-2 rounded-lg text-white bg-white/10 placeholder-white/60 border border-white/30 focus:outline-none"
              placeholder="Share your thoughts..."
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              🚀
            </button>
          </div>

          <button
            onClick={handleNewSession}
            className="mt-3 text-sm text-white/70 underline hover:text-white"
          >
            🔁 Start New Chat
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
