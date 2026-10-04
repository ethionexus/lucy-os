import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import Chat from "./components/Chat";
import SystemMonitor from "./components/SystemMonitor";
import LogViewer from "./components/LogViewer";
import Splash from "./components/Splash";
import Welcome from "./components/Welcome";
import Dock from "./components/Dock";
import TopBar from "./components/TopBar";
import ControlCenter from "./components/ControlCenter";
import Flow from "./components/Flow";
import Settings from "./components/Settings";
import CommandPalette from "./components/CommandPalette";
import AppStore from "./components/AppStore";
import "./shell.css";

interface SystemInfo {
  cpu_usage: number;
  total_memory: number;
  used_memory: number;
  total_disk: number;
  used_disk: number;
  process_count: number;
}

type Tab = "chat" | "store" | "monitor" | "logs" | "flow";

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [showWelcome, setShowWelcome] = useState(false);
  const [controlCenter, setControlCenter] = useState(false);
  const [settings, setSettings] = useState(false);
  const [palette, setPalette] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  const openStore = () => setActiveTab("store");

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

  // Global Command Palette.
  //
  // Super+Space is registered as a real global shortcut in the Rust layer
  // (src-tauri/src/lib.rs), so it works even when another window has focus.
  // The in-app key handler is a fallback for when the global grab is
  // unavailable (for example if the key is already taken).
  const togglePalette = () => setPalette((v) => !v);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    listen("lucy://toggle-palette", () => togglePalette())
      .then((fn) => {
        unlisten = fn;
      })
      .catch((e) => console.error("palette shortcut listener failed:", e));
    return () => unlisten?.();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey && e.code === "Space") {
        e.preventDefault();
        setPalette((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      {showSplash && <Splash onComplete={() => setShowSplash(false)} />}
      {!showSplash && showWelcome && (
        <Welcome onComplete={() => setShowWelcome(false)} />
      )}

      <TopBar
        onToggleControlCenter={() => setControlCenter((v) => !v)}
        onOpenSettings={() => setSettings((v) => !v)}
      />

      <div className="app">
        <main className="main">
          {activeTab === "chat" && <Chat />}
          {activeTab === "store" && <AppStore />}
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
            className={activeTab === "store" ? "active" : ""}
            onClick={() => setActiveTab("store")}
          >
            App Store
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

      <Dock
        onOpenPalette={togglePalette}
        onOpenStore={openStore}
        onOpenSettings={() => setSettings(true)}
      />
      <ControlCenter open={controlCenter} onClose={() => setControlCenter(false)} />
      {settings && <Settings onClose={() => setSettings(false)} />}
      <CommandPalette
        open={palette}
        onClose={() => setPalette(false)}
        onOpenStore={openStore}
        onOpenSettings={() => setSettings(true)}
      />
    </>
  );
}

export default App;
