import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface CommandResult {
  success: boolean;
  output: string;
  error?: string | null;
}

interface SearchHit {
  path: string;
  score: number;
  snippet: string;
}

type ItemKind = "app" | "action" | "setting" | "file" | "ai";

interface PaletteItem {
  id: string;
  kind: ItemKind;
  icon: string;
  title: string;
  subtitle?: string;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onOpenStore: () => void;
  onOpenSettings: () => void;
}

/** Apps offered for instant launch (dock targets + installed suite). */
const LAUNCHABLE: Array<{ id: string; name: string; icon: string; target: string }> = [
  { id: "browser", name: "Chromium", icon: "🌐", target: "chromium" },
  { id: "firefox", name: "Firefox", icon: "🦊", target: "firefox" },
  { id: "terminal", name: "Alacritty Terminal", icon: "⌨️", target: "alacritty" },
  { id: "files", name: "Files", icon: "📁", target: "thunar" },
  { id: "editor", name: "Code", icon: "📝", target: "code" },
  { id: "media", name: "mpv", icon: "🎬", target: "mpv" },
  { id: "celluloid", name: "Celluloid", icon: "🎞️", target: "celluloid" },
  { id: "hub", name: "Lucy Hub", icon: "🤖", target: "lucy-shell" },
];

/**
 * Global Command Palette (Super+Space).
 *
 * A Spotlight-style overlay that mixes instant app launch, in-shell actions,
 * Lucy settings toggles, offline semantic file search and an AI fallback that
 * asks the local agent to turn the query into a shell command.
 */
export default function CommandPalette({
  open,
  onClose,
  onOpenStore,
  onOpenSettings,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const [files, setFiles] = useState<SearchHit[]>([]);
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [status, setStatus] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset when the overlay is shown, and focus the field.
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelected(0);
    setFiles([]);
    setAiSuggestion(null);
    setStatus("");
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, [open]);

  const run = useCallback(
    async (item: PaletteItem) => {
      setStatus(`${item.title}…`);
      try {
        if (item.kind === "action") {
          const res = await invoke<CommandResult>("system_action", {
            action: item.id,
          });
          setStatus(res.success ? "Done" : res.error ?? "Failed");
          if (res.success) onClose();
        } else if (item.kind === "app") {
          await invoke("launch_app", { target: item.id });
          onClose();
        }
      } catch (e) {
        setStatus(String(e));
      }
    },
    [onClose],
  );

  // App + action + setting commands, filtered by the query.
  const staticItems = useMemo<PaletteItem[]>(() => {
    const apps: PaletteItem[] = LAUNCHABLE.map((a) => ({
      id: a.target,
      kind: "app",
      icon: a.icon,
      title: a.name,
      subtitle: "Application",
    }));

    const actions: PaletteItem[] = [
      { id: "store", kind: "action", icon: "🛍️", title: "App Store", subtitle: "Browse and install apps" },
      { id: "settings", kind: "action", icon: "⚙️", title: "Settings", subtitle: "Language, appearance, AI" },
      { id: "palette-help", kind: "action", icon: "❔", title: "Keyboard shortcuts", subtitle: "Super+Space, Super+Shift+Space" },
    ];

    const toggles: PaletteItem[] = [
      { id: "keyboard-toggle", kind: "setting", icon: "አማ", title: "Toggle Amharic keyboard", subtitle: "English stays the default" },
      { id: "theme-toggle", kind: "setting", icon: "🎨", title: "Toggle Heritage theme", subtitle: "Obsidian + gold accent" },
      { id: "wifi-toggle", kind: "action", icon: "📶", title: "Toggle Wi-Fi", subtitle: "Network" },
      { id: "bluetooth-toggle", kind: "action", icon: "🔵", title: "Toggle Bluetooth", subtitle: "Devices" },
      { id: "audio-toggle-mute", kind: "action", icon: "🔊", title: "Mute / unmute audio", subtitle: "Sound" },
      { id: "vpn-start", kind: "action", icon: "🛡️", title: "Start VPN", subtitle: "sing-box" },
    ];

    return [...apps, ...actions, ...toggles];
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return staticItems.filter((i) => i.kind === "app" || i.title === "App Store");
    }
    return staticItems.filter((i) =>
      `${i.title} ${i.subtitle ?? ""} ${i.kind}`.toLowerCase().includes(q),
    );
  }, [query, staticItems]);

  // Offline semantic file search, debounced.
  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (q.length < 3) {
      setFiles([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const raw = await invoke<string>("search_files", { query: q, topK: 5 });
        const parsed = JSON.parse(raw) as SearchHit[];
        if (!cancelled) setFiles(Array.isArray(parsed) ? parsed.slice(0, 5) : []);
      } catch {
        if (!cancelled) setFiles([]);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, open]);

  const items = useMemo<PaletteItem[]>(() => {
    const fileItems: PaletteItem[] = files.map((f) => ({
      id: f.path,
      kind: "file",
      icon: "📄",
      title: f.path.split("/").pop() || f.path,
      subtitle: `${f.path}  ·  ${Math.round(f.score * 100)}%`,
    }));
    const ai: PaletteItem[] = aiSuggestion
      ? [{ id: aiSuggestion, kind: "ai", icon: "✨", title: aiSuggestion, subtitle: "Ask Lucy to run this" }]
      : [];
    return [...filtered, ...ai, ...fileItems];
  }, [filtered, aiSuggestion, files]);

  useEffect(() => setSelected(0), [items.length]);

  const activate = useCallback(
    async (item: PaletteItem | undefined) => {
      if (!item) return;
      if (item.kind === "file") {
        // Open the containing directory in the file manager.
        const dir = item.id.replace(/\/[^/]*$/, "") || "/";
        await invoke("launch_app", { target: `thunar ${dir}` });
        onClose();
        return;
      }
      if (item.kind === "ai") {
        const res = await invoke<CommandResult>("execute_command", { command: item.id });
        setStatus(res.success ? res.output.trim() || "Ran." : res.error ?? "Failed");
        return;
      }
      if (item.id === "store") {
        onOpenStore();
        onClose();
        return;
      }
      if (item.id === "settings") {
        onOpenSettings();
        onClose();
        return;
      }
      if (item.id === "palette-help") {
        setStatus("Super+Space opens the palette · Super+Shift+Space switches the keyboard layout");
        return;
      }
      if (item.id === "keyboard-toggle" || item.id === "theme-toggle") {
        const res = await invoke<CommandResult>("execute_command", {
          command: item.id === "keyboard-toggle" ? "lucy-keyboard toggle" : "lucy-theme toggle",
        });
        setStatus(res.success ? res.output.trim() : res.error ?? "Failed");
        return;
      }
      await run(item);
    },
    [run, onClose, onOpenStore, onOpenSettings],
  );

  const askAi = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    setAiBusy(true);
    setStatus("Asking Lucy…");
    try {
      const res = await invoke<CommandResult>("ai_translate", { text: q });
      if (res.success && res.output.trim()) {
        setAiSuggestion(res.output.trim());
        setStatus("Press Enter to run Lucy's suggestion");
      } else {
        setAiSuggestion(null);
        setStatus("Lucy has no suggestion for that.");
      }
    } catch (e) {
      setStatus(String(e));
    } finally {
      setAiBusy(false);
    }
  }, [query]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, items.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (e.ctrlKey) void askAi();
      else void activate(items[selected]);
    }
  };

  if (!open) return null;

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <div
        className="palette-panel"
        role="dialog"
        aria-label="Command palette"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="palette-input-row">
          <span className="palette-search-icon">🔍</span>
          <input
            ref={inputRef}
            className="palette-input"
            placeholder="Search apps, files, settings — or describe what you want…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            spellCheck={false}
          />
          <button
            className="palette-ai-button"
            onClick={() => void askAi()}
            disabled={aiBusy || !query.trim()}
            title="Ask Lucy (Ctrl+Enter)"
          >
            {aiBusy ? "…" : "✨ Ask"}
          </button>
        </div>

        <ul className="palette-list">
          {items.length === 0 && (
            <li className="palette-empty">
              No matches. Press <kbd>Ctrl</kbd>+<kbd>Enter</kbd> to ask Lucy.
            </li>
          )}
          {items.map((item, i) => (
            <li
              key={`${item.kind}-${item.id}-${i}`}
              className={`palette-item ${i === selected ? "selected" : ""} kind-${item.kind}`}
              onMouseEnter={() => setSelected(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                void activate(item);
              }}
            >
              <span className="palette-item-icon">{item.icon}</span>
              <span className="palette-item-text">
                <span className="palette-item-title">{item.title}</span>
                {item.subtitle && (
                  <span className="palette-item-subtitle">{item.subtitle}</span>
                )}
              </span>
              <span className="palette-item-kind">{item.kind}</span>
            </li>
          ))}
        </ul>

        <div className="palette-footer">
          <span className="palette-status">{status}</span>
          <span className="palette-hint">
            <kbd>↑</kbd><kbd>↓</kbd> navigate · <kbd>Enter</kbd> run ·{" "}
            <kbd>Esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}
