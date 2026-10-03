import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import Chat from "./components/Chat";
import SystemMonitor from "./components/SystemMonitor";
import LogViewer from "./components/LogViewer";
import Splash from "./components/Splash";
import Welcome from "./components/Welcome";

interface SystemInfo {
  cpu_usage: number;
  total_memory: number;
  used_memory: number;
  total_disk: number;
  used_disk: number;
  process_count: number;
}

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [showWelcome, setShowWelcome] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "monitor" | "logs">("chat");

  // Play the lucy-intro welcome experience on first launch. The flag is
  // kept in the webview's localStorage, so it persists across app restarts
  // (and is naturally reset on a fresh, non-persistent live boot).
  useEffect(() => {
    let welcomed = false;
    try {
      welcomed = localStorage.getItem("lucy.welcomed") === "1";
    } catch {
      /* storage unavailable — non-fatal */
    }
    if (!welcomed) setShowWelcome(true);
  }, []);

  useEffect(() => {
    const fetchSystemInfo = async () => {
      try {
        const info = await invoke<SystemInfo>("get_system_info");
        setSystemInfo(info);
      } catch (error) {
        console.error("Failed to fetch system info:", error);
      }
    };

    fetchSystemInfo();
    const interval = setInterval(fetchSystemInfo, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {showSplash && <Splash onComplete={() => setShowSplash(false)} />}
      {!showSplash && showWelcome && (
        <Welcome onComplete={() => setShowWelcome(false)} />
      )}
      <div className="app">
        <header className="header">
          <h1>Lucy OS</h1>
          <nav className="nav">
          <button
            className={activeTab === "chat" ? "active" : ""}
            onClick={() => setActiveTab("chat")}
          >
            Chat
          </button>
          <button
            className={activeTab === "monitor" ? "active" : ""}
            onClick={() => setActiveTab("monitor")}
          >
            Monitor
          </button>
          <button
            className={activeTab === "logs" ? "active" : ""}
            onClick={() => setActiveTab("logs")}
          >
            Logs
          </button>
        </nav>
      </header>

      <main className="main">
        {activeTab === "chat" && <Chat />}
        {activeTab === "monitor" && systemInfo && (
          <SystemMonitor info={systemInfo} />
        )}
        {activeTab === "logs" && <LogViewer />}
      </main>

      <style>{`
        .app {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: #1a1a1a;
          color: #e0e0e0;
        }

        .header {
          padding: 1rem 2rem;
          background: #2d2d2d;
          border-bottom: 1px solid #3d3d3d;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .header h1 {
          margin: 0;
          font-size: 1.5rem;
        }

        .nav {
          display: flex;
          gap: 0.5rem;
        }

        .nav button {
          padding: 0.5rem 1rem;
          background: #3d3d3d;
          border: none;
          border-radius: 4px;
          color: #e0e0e0;
          cursor: pointer;
          transition: background 0.2s;
        }

        .nav button:hover {
          background: #4d4d4d;
        }

        .nav button.active {
          background: #6366f1;
        }

        .main {
          flex: 1;
          overflow: auto;
          padding: 1rem;
        }
      `}</style>
    </div>
    </>
  );
}

export default App;
