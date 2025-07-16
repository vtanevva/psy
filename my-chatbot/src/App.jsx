"use client";

import { useState, useEffect, useRef } from "react";
import VoiceChat from "./pages/VoiceChat";
import Dropdown from "./pages/Dropdown";

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
  const [sessionName, setSessionName] = useState("");

  const chatContainerRef = useRef(null);
  const generateSessionId = (id) => `${id}-${crypto.randomUUID().slice(0, 8)}`;

  // auto-scroll on new chat
  useEffect(() => {
    const el = chatContainerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [chat]);

  // fetch sessions for user
  const fetchSessions = async (id = userId) => {
    if (!id) return;
    try {
      const res = await fetch("/api/sessions-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: id }),
      });
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error("❌ Failed to fetch sessions:", err);
    }
  };

  // auto-generate session title (after 3 user msgs)
  const generateSessionName = async (messages) => {
    if (!messages || messages.length < 5) return; // guard: need at least 3 user + bot replies
    const userMsgs = messages.filter((m) => m.role === "user");
    if (userMsgs.length < 3) return;

    try {
      const facts = messages.map((m) => `- ${m.text}`).join("\n");
      const prompt = `
Based on this short conversation, generate a short, relevant title (max 6 words).
Use the user's intent, topic, or tone.

Conversation:
${facts}

Title:
      `.trim();

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: prompt,
          user_id: userId,
          session_id: sessionId,
        }),
      });

      const data = await res.json();
      const name = (data.reply || "Untitled").trim().replace(/^["']|["']$/g, "");
      setSessionName(name);

      await fetch("/api/save-session-name", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          session_id: sessionId,
          name,
        }),
      });

      setTimeout(() => fetchSessions(), 200);
    } catch (err) {
      console.error("❌ Failed to generate session name:", err);
    }
  };

  // user enters name & starts chat
  const handleStart = async (e) => {
    e.preventDefault();
    const cleanUser = userId.toLowerCase().trim();
    if (!cleanUser) return;

    const newSession = generateSessionId(cleanUser);
    setUserId(cleanUser);
    setSessionId(newSession);
    setEntered(true);
    setChat([]);
    setSelectedSession(null);
    setSessionName("");

    setTimeout(() => fetchSessions(cleanUser), 300);
  };

  // send message
  const handleSend = async () => {
    if (!input.trim()) return;
    const msgText = input;
    setInput("");

    const userMessage = { role: "user", text: msgText };
    const updatedChat = [...chat, userMessage];
    setChat(updatedChat);
    setLoading(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msgText,
          user_id: userId,
          session_id: sessionId,
        }),
      });

      const data = await res.json();
      const botMessage = { role: "assistant", text: data.reply };
      const newChat = [...updatedChat, botMessage];
      setChat(newChat);

      if (!sessionName) {
        const userMsgs = newChat.filter((m) => m.role === "user");
        if (userMsgs.length === 3) {
          generateSessionName(newChat);
        }
      }
    } catch (err) {
      console.error("❌ Error talking to backend:", err);
    } finally {
      setLoading(false);
    }
  };

  // start new chat
  const handleNewSession = () => {
    const newSessionId = generateSessionId(userId);
    setSessionId(newSessionId);
    setChat([]);
    setSelectedSession(null);
    setSessionName("");
    setTimeout(() => fetchSessions(), 200);
  };

  // load session from dropdown
  const handleSessionSelect = async (eOrValue) => {
    const selected = typeof eOrValue === "string" ? eOrValue : eOrValue.target.value;
    setSelectedSession(selected);
    setSessionId(selected);
    try {
      const res = await fetch("/api/session_chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, session_id: selected }),
      });
      const data = await res.json();
      // DB returns {chat:[...]} with role 'user' & 'bot'
      // Normalize to user/assistant for UI
      const normalized = (data.chat || []).map((m) => ({
        role: m.role === "bot" ? "assistant" : m.role,
        text: m.text,
      }));
      setChat(normalized);
    } catch (err) {
      console.error("Error loading chat:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex flex-col items-center p-6 relative overflow-hidden">
      {!entered ? (
        <form onSubmit={handleStart} className="text-center space-y-6 mt-32">
          <img src="/robot-emoji.png" alt="Chatbot Logo" className="max-w-full h-auto mb-4" />
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter your name"
            className="px-4 py-2 rounded-lg text-center text-white bg-white/10 border border-white/30 placeholder-white/60 focus:outline-none"
            required
          />
          <br />
          <button type="submit" className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">
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

          {sessions.length > 0 && (
            <Dropdown
              sessions={sessions}
              selectedSession={selectedSession}
              onSelect={(value) => handleSessionSelect(value)}
            />
          )}

          <div
            ref={chatContainerRef}
            className="overflow-y-auto space-y-4 px-2 mb-4"
            style={{ height: "400px", scrollBehavior: "smooth" }}
          >
            {chat.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
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
