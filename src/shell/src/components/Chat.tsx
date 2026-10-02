import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hello! I'm Lucy, your AI assistant. How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // For now, execute command directly
      // In production, this would go through the AI agent
      const result = await invoke<string>("execute_command", { command: input });
      const assistantMessage: Message = {
        role: "assistant",
        content: result || "Command executed successfully",
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${error}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {loading && <div className="message assistant">Thinking...</div>}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          placeholder="Type a command or ask a question..."
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>

      <style>{`
        .chat {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        .messages {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .message {
          max-width: 80%;
          padding: 0.75rem 1rem;
          border-radius: 8px;
        }

        .message.user {
          align-self: flex-end;
          background: #6366f1;
          color: white;
        }

        .message.assistant {
          align-self: flex-start;
          background: #3d3d3d;
          color: #e0e0e0;
        }

        .message-content {
          white-space: pre-wrap;
          word-break: break-word;
        }

        .input-area {
          display: flex;
          gap: 0.5rem;
          padding: 1rem;
          background: #2d2d2d;
          border-top: 1px solid #3d3d3d;
        }

        .input-area input {
          flex: 1;
          padding: 0.75rem;
          background: #3d3d3d;
          border: 1px solid #4d4d4d;
          border-radius: 4px;
          color: #e0e0e0;
          font-size: 1rem;
        }

        .input-area input:focus {
          outline: none;
          border-color: #6366f1;
        }

        .input-area button {
          padding: 0.75rem 1.5rem;
          background: #6366f1;
          border: none;
          border-radius: 4px;
          color: white;
          cursor: pointer;
          font-size: 1rem;
        }

        .input-area button:hover:not(:disabled) {
          background: #5558e3;
        }

        .input-area button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
