import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from './App';
import VoiceChat from './pages/VoiceChat'; // ✅ make sure path is correct
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/voice" element={<VoiceChat />} />
    </Routes>
  </BrowserRouter>
);
