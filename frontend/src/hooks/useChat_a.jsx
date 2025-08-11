import { createContext, useContext, useEffect, useState } from "react";

const backendUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

const ChatContext = createContext();

export const ChatProvider = ({ children }) => {
  const chat = async (message) => {
    setLoading(true);
    const data = await fetch(`${backendUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    });
    const resp = (await data.json()).messages;
    setMessages((messages) => [...messages, ...resp]);
    setLoading(false);
  };

  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState();
  const [loading, setLoading] = useState(false);
  const [cameraZoomed, setCameraZoomed] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false); // ✅ toggle state for history box

  const onMessagePlayed = () => {
    // ✅ Instead of deleting, just mark message as played
    setMessages((messages) => {
      if (messages.length > 0) {
        return [{ ...messages[0], played: true }, ...messages.slice(1)];
      }
      return messages;
    });
  };

  useEffect(() => {
    if (messages.length > 0) {
      setMessage(messages[0]);
    } else {
      setMessage(null);
    }
  }, [messages]);

  return (
    <ChatContext.Provider
      value={{
        chat,
        message,
        messages, // ✅ expose full chat history
        onMessagePlayed,
        loading,
        cameraZoomed,
        setCameraZoomed,
        historyOpen,
        setHistoryOpen, // ✅ allow toggle control from UI
      }}
    >
      {children}
      {/* ✅ Floating translucent chat history box */}
      <div
        style={{
          position: "fixed",
          bottom: "10px",
          right: "10px",
          background: "rgba(0, 0, 0, 0.5)",
          color: "#fff",
          padding: "10px",
          borderRadius: "8px",
          maxWidth: "300px",
          maxHeight: historyOpen ? "400px" : "40px",
          overflowY: "auto",
          transition: "all 0.3s ease",
          fontSize: "14px",
          zIndex: 9999,
        }}
      >
        <div
          style={{
            cursor: "pointer",
            fontWeight: "bold",
            marginBottom: historyOpen ? "10px" : "0",
            userSelect: "none",
          }}
          onClick={() => setHistoryOpen(!historyOpen)}
        >
          {historyOpen ? "Hide Chat History" : "Show Chat History"}
        </div>
        {historyOpen &&
          messages.map((m, idx) => (
            <div key={idx} style={{ marginBottom: "5px", opacity: m.played ? 0.6 : 1 }}>
              {m.role === "user" ? "🧑: " : "🤖: "}
              {m.content}
            </div>
          ))}
      </div>
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
