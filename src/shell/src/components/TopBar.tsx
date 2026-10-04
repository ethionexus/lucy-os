import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";

interface CommandResult {
  success: boolean;
  output: string;
  error?: string | null;
}

interface TopBarProps {
  onToggleControlCenter: () => void;
  onOpenSettings: () => void;
}

export default function TopBar({ onToggleControlCenter, onOpenSettings }: TopBarProps) {
  const [now, setNow] = useState(new Date());
  const [wifi, setWifi] = useState<boolean | null>(null);
  const [bluetooth, setBluetooth] = useState<boolean | null>(null);
  const [muted, setMuted] = useState<boolean | null>(null);
  const [vpn, setVpn] = useState<boolean | null>(null);
  // Week 4: optional Amharic/Ethiopic input layout (English is the default).
  const [amharic, setAmharic] = useState(false);

  // Keep the layout indicator in sync with the system (it can also be flipped
  // with the Super+Space keybind, outside the shell).
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await invoke<CommandResult>("keyboard_layout", {
          action: { action: "status" },
        });
        if (!cancelled && res?.success) {
          setAmharic(res.output.trim() === "amharic");
        }
      } catch { /* optional feature, ignore */ }
    };
    check();
    const t = setInterval(check, 4000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  const toggleKeyboard = async () => {
    const next = amharic ? "english" : "amharic";
    try {
      await invoke<CommandResult>("keyboard_layout", { action: { action: next } });
      setAmharic(next === "amharic");
    } catch (e) {
      console.error("Keyboard layout toggle failed:", e);
    }
  };

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const w = await invoke<CommandResult>("system_action", { action: "wifi-status" });
      setWifi(/enabled/i.test(w.output));
    } catch { /* ignore */ }
    try {
      const b = await invoke<CommandResult>("system_action", { action: "bluetooth-status" });
      setBluetooth(/yes/i.test(b.output));
    } catch { /* ignore */ }
    try {
      const m = await invoke<CommandResult>("system_action", { action: "audio-status" });
      setMuted(/yes/i.test(m.output));
    } catch { /* ignore */ }
    try {
      const v = await invoke<CommandResult>("system_action", { action: "vpn-status" });
      setVpn(/active/i.test(v.output));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  const toggle = async (action: string) => {
    try {
      await invoke("system_action", { action });
      await refresh();
    } catch (e) {
      console.error("toggle failed:", e);
    }
  };

  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const date = now.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });

  return (
    <header className="topbar">
      <div className="topbar-left">
        <span className="topbar-brand">Lucy OS</span>
      </div>

      <div className="topbar-center">
        <span className="topbar-clock">{time}</span>
        <span className="topbar-date">{date}</span>
      </div>

      <div className="topbar-right">
        <button
          className={`status-icon ${wifi ? "on" : ""}`}
          title="Wi-Fi"
          onClick={() => toggle("wifi-toggle")}
        >
          📶
        </button>
        <button
          className={`status-icon ${bluetooth ? "on" : ""}`}
          title="Bluetooth"
          onClick={() => toggle("bluetooth-toggle")}
        >
          🔵
        </button>
        <button
          className={`status-icon ${muted ? "" : "on"}`}
          title="Audio"
          onClick={() => toggle("audio-toggle-mute")}
        >
          {muted ? "🔇" : "🔊"}
        </button>
        <button
          className={`status-icon ${vpn ? "on" : ""}`}
          title="VPN"
          onClick={() => toggle(vpn ? "vpn-stop" : "vpn-start")}
        >
          🛡️
        </button>
        <button
          className={`status-icon keyboard-toggle ${amharic ? "on" : ""}`}
          title={
            amharic
              ? "Input layout: Amharic (Ethiopic) - click for English"
              : "Input layout: English - click for Amharic (Super+Space)"
          }
          onClick={toggleKeyboard}
        >
          {amharic ? "አማ" : "EN"}
        </button>
        <button
          className="status-icon"
          title="Settings"
          onClick={onOpenSettings}
        >
          ⚙️
        </button>
        <button
          className="status-icon control-center-toggle"
          title="Control Center"
          onClick={onToggleControlCenter}
        >
          🎛️
        </button>
      </div>
    </header>
  );
}
