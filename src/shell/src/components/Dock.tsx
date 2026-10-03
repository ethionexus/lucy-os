import { invoke } from "@tauri-apps/api/core";

interface DockApp {
  id: string;
  name: string;
  icon: string;
  target: string;
}

const APPS: DockApp[] = [
  { id: "browser", name: "Browser", icon: "🌐", target: "chromium" },
  { id: "files", name: "Files", icon: "📁", target: "thunar" },
  { id: "terminal", name: "Terminal", icon: "⌨️", target: "alacritty" },
  { id: "media", name: "Media", icon: "🎬", target: "mpv" },
  { id: "hub", name: "Lucy Hub", icon: "🤖", target: "lucy-shell" },
  { id: "settings", name: "Settings", icon: "⚙️", target: "lxappearance" },
];

export default function Dock() {
  const launch = async (target: string) => {
    try {
      await invoke("launch_app", { target });
    } catch (e) {
      console.error("launch failed:", e);
    }
  };

  return (
    <nav className="dock" aria-label="Application dock">
      <div className="dock-inner">
        {APPS.map((app) => (
          <button
            key={app.id}
            className="dock-icon"
            title={app.name}
            onClick={() => launch(app.target)}
          >
            <span className="dock-icon-glyph">{app.icon}</span>
            <span className="dock-icon-label">{app.name}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
