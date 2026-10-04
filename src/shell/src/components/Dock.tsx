import { invoke } from "@tauri-apps/api/core";

interface DockApp {
  id: string;
  name: string;
  icon: string;
  /** Launch an external application by desktop name / command. */
  target?: string;
  /** Or run an in-shell action instead. */
  action?: "palette" | "store";
}

const APPS: DockApp[] = [
  { id: "search", name: "Search", icon: "🔍", action: "palette" },
  { id: "store", name: "App Store", icon: "🛍️", action: "store" },
  { id: "browser", name: "Browser", icon: "🌐", target: "chromium" },
  { id: "files", name: "Files", icon: "📁", target: "thunar" },
  { id: "terminal", name: "Terminal", icon: "⌨️", target: "alacritty" },
  { id: "media", name: "Media", icon: "🎬", target: "mpv" },
  { id: "hub", name: "Lucy Hub", icon: "🤖", target: "lucy-shell" },
  { id: "settings", name: "Settings", icon: "⚙️", target: "lxappearance" },
];

interface DockProps {
  onOpenPalette: () => void;
  onOpenStore: () => void;
}

export default function Dock({ onOpenPalette, onOpenStore }: DockProps) {
  const launch = async (app: DockApp) => {
    if (app.action === "palette") {
      onOpenPalette();
      return;
    }
    if (app.action === "store") {
      onOpenStore();
      return;
    }
    if (!app.target) return;
    try {
      await invoke("launch_app", { target: app.target });
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
            onClick={() => void launch(app)}
          >
            <span className="dock-icon-glyph">{app.icon}</span>
            <span className="dock-icon-label">{app.name}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
