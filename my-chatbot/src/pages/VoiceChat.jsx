import React, { useState, useRef } from 'react';
import axios from 'axios';

export default function VoiceChat({ userId, sessionId }) {
  const [text, setText] = useState('');
  const [response, setResponse] = useState('');
  const recognitionRef = useRef(null);

  const handleStart = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech Recognition is not supported in this browser 😢");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = async (event) => {
      const transcript = event.results[0][0].transcript;
      setText(transcript);
      await sendToBot(transcript);
    };

    recognition.onerror = (event) => {
      console.error('Recognition error:', event.error);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const handleStop = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
  };

  const sendToBot = async (userInput) => {
    try {
      const res = await axios.post('http://127.0.0.1:5555/chat', {
        user_id: userId,
        message: userInput,
        session_id: sessionId,
      });

      const botReply = res.data.reply;
      setResponse(botReply);
      speak(botReply);
    } catch (err) {
      console.error('❌ Error sending to bot:', err);
    }
  };

  const speak = (text) => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <h2 className="text-xl font-bold mb-4">🎙️ Voice Chat</h2>

      <div className="mb-2">
        <button onClick={handleStart} className="bg-blue-500 text-white px-4 py-2 rounded mr-2">
          Start Talking
        </button>
        <button onClick={handleStop} className="bg-red-500 text-white px-4 py-2 rounded">
          Stop
        </button>
      </div>

      <textarea
        rows="2"
        className="w-full max-w-md p-2 border rounded mb-2"
        value={text}
        readOnly
        placeholder="Your spoken input..."
      />
      <textarea
        rows="2"
        className="w-full max-w-md p-2 border rounded"
        value={response}
        readOnly
        placeholder="Bot response..."
      />
    </div>
  );
}
