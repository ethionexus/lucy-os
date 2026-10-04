import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface CommandResult {
  success: boolean;
  output: string;
  error?: string | null;
}

interface CatalogApp {
  id: string;
  name: string;
  category: string;
  description?: string;
  kind: string;
  core?: boolean;
  native_package?: string | null;
}

interface CatalogPayload {
  version: number;
  remote_name: string;
  remote_url: string;
  apps: CatalogApp[];
}

interface StatusPayload {
  flatpak_installed: boolean;
  flathub_configured: boolean;
  remotes: string[];
  catalog_version: number;
  catalog_apps: number;
  core_apps: string[];
  installed: number;
}

interface InstalledRow {
  application: string;
  name: string;
  version: string;
  origin?: string;
}

/** Parse a JSON payload out of an `invoke` CommandResult. */
function parseJson<T>(res: CommandResult): T | null {
  if (!res?.success) return null;
  try {
    return JSON.parse(res.output) as T;
  } catch {
    return null;
  }
}

const KIND_LABEL: Record<string, string> = {
  flatpak: "Flatpak",
  native: "Pre-installed",
};

/**
 * Graphical App Store.
 *
 * Talks to all seven appstore RPCs: app_catalog, app_search, app_install,
 * app_remove, app_installed, app_status and app_flathub_setup. Everything is
 * opt-in: when Flatpak is missing the pane still shows the curated catalog
 * and offers a one-click "Enable Flathub" action.
 */
export default function AppStore() {
  const [catalog, setCatalog] = useState<CatalogApp[]>([]);
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [installed, setInstalled] = useState<InstalledRow[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    try {
      const catRes = await invoke<CommandResult>("app_catalog");
      const payload = parseJson<CatalogPayload>(catRes);
      if (payload) setCatalog(payload.apps);

      const statusRes = await invoke<CommandResult>("app_status");
      setStatus(parseJson<StatusPayload>(statusRes));

      const instRes = await invoke<CommandResult>("app_installed");
      const instPayload = parseJson<{ installed: InstalledRow[] }>(instRes);
      setInstalled(instPayload?.installed ?? []);
    } catch (e) {
      setMessage(String(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
    // If the user typed a search, keep it live against Flathub too.
  }, [refresh]);

  const installedIds = useMemo(
    () => new Set(installed.map((r) => r.application)),
    [installed],
  );

  const categories = useMemo(() => {
    const set = new Set<string>();
    catalog.forEach((a) => set.add(a.category));
    return ["all", ...Array.from(set).sort()];
  }, [catalog]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return catalog.filter((a) => {
      if (category !== "all" && a.category !== category) return false;
      if (!q) return true;
      return `${a.name} ${a.id} ${a.description ?? ""}`.toLowerCase().includes(q);
    });
  }, [catalog, category, query]);

  const doInstall = async (app: CatalogApp) => {
    setBusy(app.id);
    setMessage(`Installing ${app.name}…`);
    try {
      const res = await invoke<CommandResult>("app_install", { appId: app.id });
      setMessage(res.success ? `${app.name} installed.` : res.error ?? "Install failed.");
      await refresh();
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(null);
    }
  };

  const doRemove = async (app: CatalogApp) => {
    setBusy(app.id);
    setMessage(`Removing ${app.name}…`);
    try {
      const res = await invoke<CommandResult>("app_remove", { appId: app.id });
      setMessage(res.success ? `${app.name} removed.` : res.error ?? "Remove failed.");
      await refresh();
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(null);
    }
  };

  const enableFlathub = async () => {
    setBusy("flathub");
    setMessage("Adding the Flathub remote…");
    try {
      const res = await invoke<CommandResult>("app_flathub_setup");
      setMessage(res.success ? "Flathub enabled." : res.error ?? "Could not enable Flathub.");
      await refresh();
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(null);
    }
  };

  const searchFlathub = async () => {
    if (!query.trim()) return;
    setBusy("search");
    try {
      const res = await invoke<CommandResult>("app_search", { query });
      const payload = parseJson<{ results: CatalogApp[] }>(res);
      const results = payload?.results ?? [];
      if (results.length) {
        setCategory("all");
        // Merge Flathub-only hits into the visible list.
        setCatalog((prev) => {
          const known = new Set(prev.map((p) => p.id));
          const extra = results
            .filter((r) => r.id && !known.has(r.id))
            .map((r) => ({ ...r, kind: "flatpak", category: "flathub" }));
          return [...prev, ...extra];
        });
        setMessage(`${results.length} result(s) from Flathub.`);
      } else {
        setMessage("No Flathub results.");
      }
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="store">
      <header className="store-header">
        <div className="store-title-row">
          <h2>App Store</h2>
          <div className="store-badges">
            <span className={`store-badge ${status?.flatpak_installed ? "on" : "off"}`}>
              Flatpak {status?.flatpak_installed ? "ready" : "missing"}
            </span>
            <span className={`store-badge ${status?.flathub_configured ? "on" : "off"}`}>
              Flathub {status?.flathub_configured ? "enabled" : "off"}
            </span>
            <span className="store-badge neutral">{installed.length} installed</span>
          </div>
        </div>

        <div className="store-controls">
          <input
            className="store-search"
            placeholder="Search apps…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void searchFlathub();
            }}
          />
          <button className="cc-btn" onClick={() => void searchFlathub()} disabled={busy !== null}>
            {busy === "search" ? "Searching…" : "Search Flathub"}
          </button>
          {status && !status.flathub_configured && (
            <button className="cc-btn primary" onClick={() => void enableFlathub()} disabled={busy !== null}>
              {busy === "flathub" ? "Enabling…" : "Enable Flathub"}
            </button>
          )}
          <button className="cc-btn" onClick={() => void refresh()} disabled={busy !== null}>
            Refresh
          </button>
        </div>

        <div className="store-categories">
          {categories.map((c) => (
            <button
              key={c}
              className={`store-category ${c === category ? "active" : ""}`}
              onClick={() => setCategory(c)}
            >
              {c}
            </button>
          ))}
        </div>
      </header>

      {message && <div className="store-message">{message}</div>}

      <div className="store-grid">
        {visible.map((app) => {
          const isInstalled = installedIds.has(app.id) || app.kind === "native";
          return (
            <article key={app.id} className="store-card">
              <div className="store-card-head">
                <span className="store-card-icon">
                  {app.kind === "native" ? "📦" : "🛍️"}
                </span>
                <div className="store-card-titles">
                  <h3>{app.name}</h3>
                  <span className="store-card-id">{app.id}</span>
                </div>
              </div>
              <p className="store-card-desc">{app.description}</p>
              <div className="store-card-foot">
                <span className="store-card-kind">
                  {KIND_LABEL[app.kind] ?? app.kind}
                  {app.core ? " · core" : ""}
                </span>
                {app.kind === "native" ? (
                  <span className="store-card-state">installed</span>
                ) : isInstalled ? (
                  <button
                    className="cc-btn"
                    onClick={() => void doRemove(app)}
                    disabled={busy !== null}
                  >
                    {busy === app.id ? "…" : "Remove"}
                  </button>
                ) : (
                  <button
                    className="cc-btn primary"
                    onClick={() => void doInstall(app)}
                    disabled={busy !== null}
                  >
                    {busy === app.id ? "…" : "Install"}
                  </button>
                )}
              </div>
            </article>
          );
        })}
        {visible.length === 0 && (
          <div className="store-empty">
            Nothing matches. Try “Search Flathub” to look beyond the catalog.
          </div>
        )}
      </div>
    </div>
  );
}
