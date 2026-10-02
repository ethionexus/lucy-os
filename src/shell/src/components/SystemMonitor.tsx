interface SystemInfo {
  cpu_usage: number;
  total_memory: number;
  used_memory: number;
  total_disk: number;
  used_disk: number;
  process_count: number;
}

interface Props {
  info: SystemInfo;
}

export default function SystemMonitor({ info }: Props) {
  const formatBytes = (bytes: number) => {
    const units = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
      bytes /= 1024;
      i++;
    }
    return `${bytes.toFixed(2)} ${units[i]}`;
  };

  const formatPercent = (value: number) => `${value.toFixed(1)}%`;

  return (
    <div className="monitor">
      <h2>System Resources</h2>

      <div className="metrics">
        <div className="metric">
          <h3>CPU Usage</h3>
          <div className="value">{formatPercent(info.cpu_usage)}</div>
          <div className="bar">
            <div className="fill" style={{ width: `${info.cpu_usage}%` }} />
          </div>
        </div>

        <div className="metric">
          <h3>Memory</h3>
          <div className="value">
            {formatBytes(info.used_memory)} / {formatBytes(info.total_memory)}
          </div>
          <div className="bar">
            <div
              className="fill"
              style={{ width: `${(info.used_memory / info.total_memory) * 100}%` }}
            />
          </div>
        </div>

        <div className="metric">
          <h3>Disk</h3>
          <div className="value">
            {formatBytes(info.used_disk)} / {formatBytes(info.total_disk)}
          </div>
          <div className="bar">
            <div
              className="fill"
              style={{ width: `${(info.used_disk / info.total_disk) * 100}%` }}
            />
          </div>
        </div>

        <div className="metric">
          <h3>Processes</h3>
          <div className="value">{info.process_count}</div>
        </div>
      </div>

      <style>{`
        .monitor {
          padding: 1rem;
        }

        .monitor h2 {
          margin-bottom: 1.5rem;
        }

        .metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .metric {
          background: #2d2d2d;
          padding: 1.5rem;
          border-radius: 8px;
        }

        .metric h3 {
          margin: 0 0 0.5rem 0;
          font-size: 0.9rem;
          color: #a0a0a0;
        }

        .metric .value {
          font-size: 1.5rem;
          font-weight: bold;
          margin-bottom: 0.5rem;
        }

        .metric .bar {
          height: 8px;
          background: #3d3d3d;
          border-radius: 4px;
          overflow: hidden;
        }

        .metric .fill {
          height: 100%;
          background: #6366f1;
          transition: width 0.3s ease;
        }
      `}</style>
    </div>
  );
}
