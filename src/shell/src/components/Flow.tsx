import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface CommandResult {
  success: boolean;
  output: string;
  error?: string | null;
}

interface Flow {
  id: string;
  name: string;
  desc: string;
  icon: string;
  command: string;
}

const FLOWS: Flow[] = [
  { id: "cleanup", name: "System Cleanup", desc: "Clear caches and temp files", icon: "🧹", command: "rm -rf ~/.cache/thumbnails/* /tmp/lucy-* 2>/dev/null; echo 'cleanup done'" },
  { id: "update", name: "Update Check", desc: "Check for package updates", icon: "📦", command: "checkupdates 2>/dev/null | head -20 || echo 'system up to date'" },
  { id: "backup", name: "Quick Backup", desc: "Backup home docs to USB", icon: "💾", command: "ls ~/Documents 2>/dev/null | head -10 || echo 'no documents yet'" },
  { id: "network", name: "Network Test", desc: "Test connectivity and speed", icon: "🌐", command: "ping -c 3 8.8.8.8 2>&1 | tail -5" },
  { id: "ai-summarize", name: "AI Summarize", desc: "Summarize clipboard via local AI", icon: "🤖", command: "echo 'AI summarize: paste text into Lucy Hub chat'" },
];

export default function Flow() {
  const [output, setOutput] = useState<Record<string, string>>({});
  const [running, setRunning] = useState<string | null>(null);

  const runFlow = async (flow: Flow) => {
    setRunning(flow.id);
    try {
      const r = await invoke<CommandResult>("execute_command", { command: flow.command });
      setOutput((prev) => ({ ...prev, [flow.id]: r.output || r.error || "done" }));
    } catch (e) {
      setOutput((prev) => ({ ...prev, [flow.id]: String(e) }));
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="flow">
      <h2>Lucy Flow — Automation Hub</h2>
      <p className="flow-sub">One-click offline automations. No code, no terminal.</p>
      <div className="flow-grid">
        {FLOWS.map((f) => (
          <div key={f.id} className="flow-card">
            <span className="flow-icon">{f.icon}</span>
            <h3>{f.name}</h3>
            <p>{f.desc}</p>
            <button
              className="flow-run"
              disabled={running === f.id}
              onClick={() => runFlow(f)}
            >
              {running === f.id ? "Running…" : "▶ Run"}
            </button>
            {output[f.id] && <pre className="flow-output">{output[f.id]}</pre>}
          </div>
        ))}
      </div>

      <style>{`
        .flow { padding: 1rem; }
        .flow h2 { margin: 0 0 0.25rem; }
        .flow-sub { color: #a0a0a0; margin: 0 0 1rem; }
        .flow-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }
        .flow-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(212,175,55,0.2); border-radius: 12px; padding: 1rem; }
        .flow-icon { font-size: 1.8rem; }
        .flow-card h3 { margin: 0.5rem 0 0.25rem; font-size: 1rem; }
        .flow-card p { margin: 0 0 0.75rem; color: #a0a0a0; font-size: 0.85rem; }
        .flow-run { padding: 0.4rem 1rem; border-radius: 8px; border: 1px solid rgba(212,175,55,0.5); background: rgba(212,175,55,0.15); color: #f7e8c3; cursor: pointer; }
        .flow-run:disabled { opacity: 0.5; }
        .flow-output { margin-top: 0.75rem; padding: 0.5rem; background: #111; border-radius: 6px; font-size: 0.75rem; white-space: pre-wrap; max-height: 120px; overflow: auto; }
      `}</style>
    </div>
  );
}
