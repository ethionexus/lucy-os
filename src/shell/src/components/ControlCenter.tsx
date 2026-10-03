import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

interface CommandResult {
  success: boolean;
  output: string;
  error?: string | null;
}

interface ControlCenterProps {
  open: boolean;
  onClose: () => void;
}

interface Toggle {
  id: string;
  name: string;
  icon: string;
  action: string;
  statusAction: string;
  active: boolean;
}

const WALLPAPERS = [
  { id: "live", name: "Lucy Live", desc: "lucy-wallpaper-live.mp4", action: "wallpaper-live" },
  { id: "launch", name: "Lucy Launch", desc: "lucy-launch.mp4", action: "wallpaper-launch" },
  { id: "static", name: "Static", desc: "Openbox wallpaper", action: "wallpaper-static" },
];

export default function ControlCenter({ open, onClose }: ControlCenterProps) {
  const [toggles, setToggles] = useState<Toggle[]>([
    { id: "wifi", name: "Wi-Fi", icon: "📶", action: "wifi-toggle", statusAction: "wifi-status", active: false },
    { id: "bluetooth", name: "Bluetooth", icon: "🔵", action: "bluetooth-toggle", statusAction: "bluetooth-status", active: false },
    { id: "audio", name: "Audio", icon: "🔊", action: "audio-toggle-mute", statusAction: "audio-status", active: true },
    { id: "vpn", name: "VPN", icon: "🛡️", action: "vpn-start", statusAction: "vpn-status", active: false },
  ]);
  const [wallpaper, setWallpaper] = useState("live");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const refresh = async () => {
      const defs = [
        { id: "wifi", statusAction: "wifi-status" },
        { id: "bluetooth", statusAction: "bluetooth-status" },
        { id: "audio", statusAction: "audio-status" },
        { id: "vpn", statusAction: "vpn-status" },
      ];
      for (const d of defs) {
        try {
          const r = await invoke<CommandResult>("system_action", { action: d.statusAction });
          const active = /enabled|yes|active/i.test(r.output);
          if (!cancelled) {
            setToggles((prev) => prev.map((x) => (x.id === d.id ? { ...x, active } : x)));
          }
        } catch { /* ignore */ }
      }
    };
    refresh();
    return () => { cancelled = true; };
  }, [open]);

  const run = async (action: string) => {
    try {
      await invoke("system_action", { action });
    } catch (e) {
      console.error("action failed:", e);
    }
  };

  const setWallpaperAction = async (action: string, id: string) => {
    try {
      await invoke("system_action", { action });
      setWallpaper(id);
    } catch (e) {
      console.error("wallpaper failed:", e);
    }
  };

  if (!open) return null;

  return (
    <div className="control-center-overlay" onClick={onClose}>
      <aside className="control-center" onClick={(e) => e.stopPropagation()}>
        <div className="cc-header">
          <h2>Control Center</h2>
          <button className="cc-close" onClick={onClose}>✕</button>
        </div>

        <div className="cc-section">
          <h3>Quick Toggles</h3>
          <div className="cc-toggles">
            {toggles.map((t) => (
              <button
                key={t.id}
                className={`cc-toggle ${t.active ? "active" : ""}`}
                onClick={() => run(t.action)}
              >
                <span className="cc-toggle-icon">{t.icon}</span>
                <span className="cc-toggle-name">{t.name}</span>
                <span className="cc-toggle-state">{t.active ? "On" : "Off"}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="cc-section">
          <h3>Wallpaper</h3>
          <div className="cc-wallpapers">
            {WALLPAPERS.map((w) => (
              <button
                key={w.id}
                className={`cc-wallpaper ${wallpaper === w.id ? "active" : ""}`}
                onClick={() => setWallpaperAction(w.action, w.id)}
              >
                <span className="cc-wallpaper-name">{w.name}</span>
                <span className="cc-wallpaper-desc">{w.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="cc-section">
          <h3>Theme</h3>
          <div className="cc-themes">
            <button className="cc-theme active">🌙 Obsidian Dark</button>
            <button className="cc-theme">☀️ Light</button>
          </div>
        </div>
      </aside>
    </div>
  );
}
