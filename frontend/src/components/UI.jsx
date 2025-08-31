import { useRef, useState, useEffect } from "react";
import { useChat } from "../hooks/useChat";

export const UI = ({ hidden, selectedModel, setSelectedModel, avatarModels }) => {
  const input = useRef();
  const scrollRef = useRef();
  const recognitionRef = useRef(null);
  const { chat, loading, message } = useChat();
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [listening, setListening] = useState(false);
  const [autoSendSpeech, setAutoSendSpeech] = useState(false); 
  const [previewTranscript, setPreviewTranscript] = useState("");

  const sendMessage = () => {
    const text = input.current.value.trim();
    if (!text || loading || message) return;

    setHistory((prev) => [...prev, { sender: "user", text }]);
    chat(text);
    input.current.value = "";
  };

  // append avatar messages
  useEffect(() => {
    if (message?.text) {
      setHistory((prev) => {
        if (prev.length && prev[prev.length - 1].text === message.text) return prev;
        return [...prev, { sender: "avatar", text: message.text }];
      });
    }
  }, [message]);

  // auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  if (hidden) return null;

  const avatarName = selectedModel.replace(".glb", "");

  // 🎤 Toggle listening
  const toggleListening = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech Recognition not supported in this browser.");
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setTimeout(() => {
        setListening(false);
      }, 2000);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);

    recognition.onresult = (event) => {
  let transcript = "";
  for (let i = event.resultIndex; i < event.results.length; i++) {
    transcript += event.results[i][0].transcript;
  }

  // 👇 live preview as you speak
  setPreviewTranscript(transcript);
  input.current.value = transcript;

  // 👇 only auto-send when it's final and auto-send is ON
  if (event.results[event.results.length - 1].isFinal) {
    if (autoSendSpeech) {
      sendMessage();
    }
  }
};

    recognition.onerror = () => {
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
    };
  };

  return (
    <div className="fixed inset-0 z-10 flex flex-col pointer-events-none p-4">
      {/* Header */}
      <div className="self-start backdrop-blur-md bg-blue-500 bg-opacity-50 p-4 rounded-lg flex flex-col gap-2 pointer-events-auto">
        <div className="mt-0">
          <label htmlFor="avatar-select" className="font-bold mr-2">
            Avatar:
          </label>
          <select
            id="avatar-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="bg-blue-600 hover:bg-blue-700 bg-opacity-50 rounded px-2 py-1 text-black font-bold cursor-pointer"
          >
            {avatarModels.map((model) => (
              <option key={model} value={model}>
                {model.replace(".glb", "").toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Toggle Chat Visibility */}
      <div className="fixed top-6 right-6 pointer-events-auto flex flex-col gap-2 items-end">
        <button
          onClick={() => setShowHistory((prev) => !prev)}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg shadow-md"
        >
          {showHistory ? "Hide Chat" : "Show Chat"}
        </button>

        {/* 🔄 Auto-send toggle */}
        <button
          onClick={() => setAutoSendSpeech((prev) => !prev)}
          className={`${
            autoSendSpeech ? "bg-blue-500 hover:bg-blue-600" : "bg-green-500 hover:bg-green-600"
          } text-white px-4 py-2 rounded-lg shadow-md`}
        >
          {autoSendSpeech ? "Auto-Send Speech: ON" : "Auto-Send Speech: OFF"}
        </button>
      </div>

      {/* Conversation history */}
      {showHistory && (
        <div
          ref={scrollRef}
          className="fixed bottom-28 left-1/2 transform -translate-x-1/2 h-60 overflow-y-auto w-full max-w-screen-sm bg-white bg-opacity-50 rounded-lg p-4 space-y-0 pointer-events-auto"
        >
          {history.map((msg, idx) =>
            msg.sender === "avatar" ? (
              <div key={idx} className="text-left">
                <div className="text-blue-600 font-bold mb-1">{avatarName.toUpperCase()}</div>
                <div className="inline-block bg-blue-500 text-white px-4 py-2 rounded-lg max-w-[80%]">
                  {msg.text}
                </div>
              </div>
            ) : (
              <div key={idx} className="text-right">
                <div className="text-green-600 font-bold mb-1">YOU</div>
                <div className="inline-block bg-green-500 text-white px-4 py-2 rounded-lg max-w-[80%]">
                  {msg.text}
                </div>
              </div>
            )
          )}
        </div>
      )}
      {/* Listening indicator */}
      {listening && (
        <div className="fixed bottom-20 left-1/2 transform -translate-x-1/2 flex gap-2 items-center pointer-events-none">
          <span className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"></span>
          <span className="w-3 h-3 bg-blue-500 rounded-full animate-bounce delay-150"></span>
          <span className="w-3 h-3 bg-blue-500 rounded-full animate-bounce delay-300"></span>
        </div>
      )}
      {/* Input bar fixed at bottom */}
      <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 flex items-center gap-2 pointer-events-auto max-w-screen-sm w-full px-2">
        <input
          className="flex-1 placeholder:text-gray-800 placeholder:italic p-4 rounded-md bg-opacity-40 bg-white backdrop-blur-md border border-blue-500 border-width-4 overflow-y-auto"
          placeholder="Type a message..."
          ref={input}
          defaultValue={previewTranscript}
          onChange={(e) => setPreviewTranscript(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
        />
        {/* 🎤 Toggle speech button */}
        <button
          onClick={toggleListening}
          className={`${
            listening ? "bg-red-500 hover:bg-red-600 text-white" : "bg-blue-500 hover:bg-blue-600 text-white"
          } px-4 py-4 rounded-md`}
        >
          {listening ? "Stop 🎤" : "Start 🎤"}
        </button>
        <button
          disabled={loading || message}
          onClick={sendMessage}
          className={`bg-blue-500 hover:bg-blue-600 text-white p-4 px-6 font-semibold uppercase rounded-md ${
            loading || message ? "cursor-not-allowed opacity-30" : ""
          }`}
        >
          Send
        </button>
      </div>
    </div>
  );
};
