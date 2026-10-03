import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import Chat from "./components/Chat";
import SystemMonitor from "./components/SystemMonitor";
import LogViewer from "./components/LogViewer";
import Splash from "./components/Splash";
import Welcome from "./components/Welcome";
import Dock from "./components/Dock";
import TopBar from "./components/TopBar";
import ControlCenter from "./components/ControlCenter";
import Flow from "./components/Flow";
import "./shell.css";

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
  const [controlCenter, setControlCenter] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "monitor" | "logs" | "flow">("chat");

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

      <TopBar onToggleControlCenter={() => setControlCenter((v) => !v)} />

      <div className="app">
        <main className="main">
          {activeTab === "chat" && <Chat />}
          {activeTab === "monitor" && systemInfo && (
            <SystemMonitor info={systemInfo} />
          )}
          {activeTab === "logs" && <LogViewer />}
          {activeTab === "flow" && <Flow />}
        </main>

        <nav className="app-nav">
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
          <button
            className={activeTab === "flow" ? "active" : ""}
            onClick={() => setActiveTab("flow")}
          >
            Flow
          </button>
        </nav>
      </div>

      <Dock />
      <ControlCenter open={controlCenter} onClose={() => setControlCenter(false)} />
    </>
  );
}

export default App;
