import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface CommandResult {
  success: boolean;
  output: string;
  error: string | null;
}

type LocaleAction = "install" | "remove" | "status";

/**
 * Settings pane.
 *
 * Week 4 (optional Amharic/Ge'ez localization) lives here. English is always
 * the default: every control below is opt-in and reverting any of them leaves
 * the system fully usable in English.
 */
export default function Settings({ onClose }: { onClose: () => void }) {
  const [keyboard, setKeyboard] = useState<"english" | "amharic">("english");
  const [locale, setLocale] = useState<"installed" | "not-installed">("not-installed");
  const [theme, setTheme] = useState<"default" | "heritage">("default");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");

  // Restore the persisted opt-in choices on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await invoke<CommandResult>("get_localization_status");
        if (cancelled || !res?.success) return;
        for (const line of res.output.split("\n")) {
          const [key, value] = line.split("=");
          if (!key || value === undefined) continue;
          const v = value.trim();
          if (key === "keyboard") setKeyboard(v === "amharic" ? "amharic" : "english");
          if (key === "locale") setLocale(v === "installed" ? "installed" : "not-installed");
          if (key === "theme") setTheme(v === "heritage" ? "heritage" : "default");
        }
      } catch (e) {
        console.error("Failed to read localization status:", e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Keep the shell's accent in sync with the Heritage toggle.
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "heritage") {
      root.setAttribute("data-theme", "heritage");
    } else {
      root.removeAttribute("data-theme");
    }
  }, [theme]);

  const run = async (cmd: string, args: Record<string, unknown>) => {
    setBusy(true);
    setStatus("");
    try {
      const res = await invoke<CommandResult>(cmd, args);
      setStatus(res.success ? res.output.trim() : res.error ?? "Command failed");
      return res;
    } catch (e) {
      setStatus(String(e));
      return null;
    } finally {
      setBusy(false);
    }
  };

  const toggleKeyboard = async () => {
    const next = keyboard === "amharic" ? "english" : "amharic";
    await run("keyboard_layout", { action: { action: next } });
    setKeyboard(next);
  };

  const doLocale = async (action: LocaleAction) => {
    const res = await run("system_locale", { action: { action } });
    if (res?.success) {
      const next = await run("system_locale", { action: { action: "status" } });
      if (next?.success) {
        setLocale(next.output.trim() === "installed" ? "installed" : "not-installed");
      }
    }
  };

  const toggleTheme = async () => {
    const next = theme === "heritage" ? "default" : "heritage";
    await run("heritage_theme", { action: { action: next } });
    setTheme(next);
  };

  return (
    <div className="cc-backdrop" onClick={onClose}>
      <div className="cc-panel settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="cc-header">
          <span>Settings</span>
          <button className="cc-close" onClick={onClose} aria-label="Close settings">
            &times;
          </button>
        </div>

        <section className="settings-section">
          <h4>Keyboard</h4>
          <p className="settings-note">
            English (US) is the default layout. Amharic (Ethiopic) is optional
            and can also be switched with Super+Space.
          </p>
          <div className="settings-row">
            <span className="settings-label">Input layout</span>
            <button className="cc-toggle" onClick={toggleKeyboard} disabled={busy}>
              <span className={keyboard === "english" ? "knob on" : "knob"} />
              <span className="cc-toggle-text">
                {keyboard === "amharic" ? "Amharic" : "English"}
              </span>
            </button>
          </div>
        </section>

        <section className="settings-section">
          <h4>Region &amp; Language</h4>
          <p className="settings-note">
            Installs the am_ET.UTF-8 locale pack. English stays the default
            language; this only makes Amharic available when you want it.
          </p>
          <div className="settings-row">
            <span className="settings-label">
              Amharic locale pack{" "}
              <em className="settings-state">
                {locale === "installed" ? "installed" : "not installed"}
              </em>
            </span>
            <span className="settings-actions">
              <button
                className="cc-btn"
                onClick={() => doLocale("install")}
                disabled={busy || locale === "installed"}
              >
                Install
              </button>
              <button
                className="cc-btn"
                onClick={() => doLocale("remove")}
                disabled={busy || locale === "not-installed"}
              >
                Disable
              </button>
            </span>
          </div>
        </section>

        <section className="settings-section">
          <h4>Appearance</h4>
          <p className="settings-note">
            The Heritage theme adds an optional Ge&apos;ez accent to the
            obsidian/gold palette. Cosmetic only &mdash; layout and language
            are unaffected.
          </p>
          <div className="settings-row">
            <span className="settings-label">
              Heritage theme{" "}
              <em className="settings-state">
                {theme === "heritage" ? "ሰላም ሐሰስ" : "off"}
              </em>
            </span>
            <button className="cc-toggle" onClick={toggleTheme} disabled={busy}>
              <span className={theme === "heritage" ? "knob on" : "knob"} />
              <span className="cc-toggle-text">
                {theme === "heritage" ? "On" : "Off"}
              </span>
            </button>
          </div>
        </section>

        <section className="settings-section">
          <h4>Lucy AI language</h4>
          <p className="settings-note">
            Optional. Prefix any request with{" "}
            <code>/lang:am</code> (or <code>/lang:fr</code>, <code>/lang:ar</code>,{" "}
            <code>/lang:es</code>, <code>/lang:zh</code>, <code>/lang:ru</code>)
            to translate in that language. Without the flag, English is used.
          </p>
        </section>

        {status && <pre className="settings-status">{status}</pre>}
      </div>
    </div>
  );
}
