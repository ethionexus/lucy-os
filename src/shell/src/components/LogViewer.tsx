import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

export default function LogViewer() {
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const logData = await invoke<string[]>("get_logs");
        setLogs(logData);
      } catch (error) {
        console.error("Failed to fetch logs:", error);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="log-viewer">
      <h2>System Logs</h2>
      <div className="log-container">
        {logs.length === 0 ? (
          <div className="empty">No logs available</div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="log-entry">
              {log}
            </div>
          ))
        )}
      </div>

      <style>{`
        .log-viewer {
          padding: 1rem;
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .log-viewer h2 {
          margin-bottom: 1rem;
        }

        .log-container {
          flex: 1;
          background: #1e1e1e;
          border-radius: 8px;
          padding: 1rem;
          overflow-y: auto;
          font-family: monospace;
          font-size: 0.9rem;
        }

        .log-entry {
          padding: 0.25rem 0;
          border-bottom: 1px solid #2d2d2d;
        }

        .log-entry:last-child {
          border-bottom: none;
        }

        .empty {
          color: #666;
          text-align: center;
          padding: 2rem;
        }
      `}</style>
    </div>
  );
}
