
import { useState, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import axios from "axios"

export default function VoiceChat({ userId, sessionId, setUseVoice }) {
  const [chat, setChat] = useState([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isSupported, setIsSupported] = useState(false)
  const [showChat, setShowChat] = useState(false)

  const recognitionRef = useRef(null)
  const chatContainerRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    setIsSupported(!!SpeechRecognition && !!window.speechSynthesis)

    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false
      recognitionRef.current.lang = "en-US"

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setInput(transcript)
        setIsListening(false)
        setTimeout(() => handleSend(transcript), 100)
      }

      recognitionRef.current.onerror = () => setIsListening(false)
      recognitionRef.current.onend = () => setIsListening(false)
    }
  }, [])

  useEffect(() => {
    chatContainerRef.current?.scrollTo({ top: chatContainerRef.current.scrollHeight, behavior: "smooth" })
  }, [chat])

  useEffect(() => {
    const last = chat.at(-1)
    if (last?.role === "bot" && !isSpeaking) speak(last.text)
  }, [chat])

  const speak = (text) => {
    if (!window.speechSynthesis) return
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 0.9
    utterance.pitch = 1
    utterance.volume = 0.8
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)
    setIsSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  const handleSend = async (msg = input) => {
    if (!msg.trim()) return
    setChat(prev => [...prev, { role: "user", text: msg }])
    setInput("")
    setLoading(true)

    try {
      const res = await axios.post("http://127.0.0.1:5555/chat", {
        message: msg,
        user_id: userId,
        session_id: sessionId,
      })
      const reply = res.data.reply
      setChat(prev => [...prev, { role: "bot", text: reply }])
    } catch (err) {
      console.error("❌ Backend error:", err)
    }
    setLoading(false)
  }

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      setIsListening(true)
      recognitionRef.current.start()
    }
  }

  const stopListening = () => {
    recognitionRef.current?.stop()
    setIsListening(false)
  }

  const stopSpeaking = () => {
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }


  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900">
      <div className="w-full max-w-3xl bg-white/10 backdrop-blur-lg border border-white/20 shadow-2xl rounded-3xl overflow-hidden">
        <div className="p-6 bg-gradient-to-r from-indigo-500/30 to-blue-500/30 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white">🎤 Voice Chat Mode</h2>
            <p className="text-sm text-white/70">User: {userId} | Session: {sessionId.slice(-8)}</p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setShowChat(!showChat)}
              className="text-white text-sm px-4 py-2 rounded-full bg-white/20 hover:bg-white/30 backdrop-blur-md transition"
            >
              {showChat ? "Hide Chat 💬" : "Show Chat 💬"}
            </button>
            <button
              onClick={() => setUseVoice(false)}
              className="text-white text-sm px-4 py-2 rounded-full bg-red-500/80 hover:bg-red-600 backdrop-blur-md transition shadow-md"
            >
              ⬅️ Back to Chat
            </button>
          </div>
        </div>

        {showChat && (
          <>
            <div ref={chatContainerRef} className="h-96 overflow-y-auto p-6 space-y-4">
              {chat.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`p-4 rounded-2xl max-w-md shadow-md text-white ${m.role === "user" ? "bg-blue-500" : "bg-gray-300 text-black"}`}>
                    {m.text}
                  </div>
                </div>
              ))}
              {loading && <div className="text-sm text-white/50 animate-pulse">🤖 Thinking...</div>}
            </div>

            <div className="p-4 border-t border-white/10 bg-gradient-to-r from-blue-500/10 to-purple-500/10">
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-white/20 backdrop-blur-md text-white p-2 rounded-xl placeholder-white/60 focus:outline-none"
                  placeholder={isListening ? "Listening..." : "Say something or type..."}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  disabled={isListening}
                />
                <button onClick={() => handleSend()} className="bg-blue-500 text-white px-4 py-2 rounded-xl hover:bg-blue-600">Send</button>
              </div>
            </div>
          </>
        )}

        <div className="p-4 flex gap-4 justify-center bg-white/5 border-t border-white/10">
          <button
            onClick={isListening ? stopListening : startListening}
            className={`px-4 py-2 rounded-full font-semibold shadow-md text-white transition ${
              isListening ? "bg-red-500" : "bg-green-500 hover:bg-green-600"
            }`}
          >
            {isListening ? "Stop Listening" : "Start Talking"}
          </button>
          {isSpeaking && (
            <button onClick={stopSpeaking} className="bg-yellow-500 text-white px-4 py-2 rounded-full hover:bg-yellow-600">🔇 Stop Speaking</button>
          )}
        </div>
      </div>
    </div>
  )
}
