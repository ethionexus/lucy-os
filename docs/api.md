# Lucy OS API Documentation

## Core Agent API

### Python API

#### LucyDaemon

Main daemon class for the AI agent.

```python
from lucy_agent import LucyDaemon

daemon = LucyDaemon(config_path="/etc/lucy/agent.conf")
await daemon.start()
```

##### Methods

**`process_command(text: str) -> dict`**

Process natural language command.

**Parameters:**
- `text`: Natural language input

**Returns:**
```python
{
    "success": bool,
    "command": str,  # if successful
    "output": str,  # command output
    "error": str,   # if failed
    "risk_level": str,  # "safe", "low", "medium", "high", "critical"
}
```

**Example:**
```python
result = await daemon.process_command("show disk usage")
print(result["output"])
```

---

**`get_system_info() -> dict`**

Get current system resource information.

**Returns:**
```python
{
    "cpu_usage": float,  # percentage
    "total_memory": int,  # bytes
    "used_memory": int,  # bytes
    "total_disk": int,  # bytes
    "used_disk": int,  # bytes
    "process_count": int
}
```

**Example:**
```python
info = await daemon.get_system_info()
print(f"CPU: {info['cpu_usage']}%")
```

---

**`start()`**

Start the daemon.

---

**`stop()`**

Stop the daemon.

---

**`run()`**

Run the daemon main loop.

#### CommandTranslator

Natural language to command translation.

```python
from lucy_agent import CommandTranslator

translator = CommandTranslator(config={'fallback_to_ollama': True})
intent = translator.translate("list files")
print(intent.command)  # "ls -la"
```

##### Methods

**`translate(text: str) -> CommandIntent`**

Translate natural language to command.

**Returns:**
```python
CommandIntent(
    command: str,
    confidence: float,
    explanation: str
)
```

---

**`add_pattern(pattern: str, command: str)`**

Add a new translation pattern.

---

**`get_patterns() -> List[str]`**

Get all registered patterns.

---

**`has_internet() -> bool`**

Check if internet connection is available.

---

**`translate_with_ollama(text: str) -> CommandIntent`**

Translate using local Ollama when offline.

#### SafetyValidator

Command safety validation.

```python
from lucy_agent import SafetyValidator

validator = SafetyValidator()
check = validator.validate("rm -rf /")
print(check.is_safe)  # False
```

##### Methods

**`validate(command: str) -> SafetyCheck`**

Validate a command for safety.

**Returns:**
```python
SafetyCheck(
    is_safe: bool,
    risk_level: str,  # "safe", "low", "medium", "high", "critical"
    reason: str,
    requires_confirmation: bool
)
```

---

**`add_dangerous_pattern(pattern: str)`**

Add a dangerous pattern.

---

**`add_safe_command(command: str)`**

Add a safe command.

#### AutoHealDaemon

Auto-healing system daemon for resource management.

```python
from lucy_agent import AutoHealDaemon

daemon = AutoHealDaemon(config_path="/etc/lucy/agent.conf")
await daemon.run()
```

##### Methods

**`check_memory() -> bool`**

Check if memory usage exceeds threshold.

**Returns:** `True` if threshold exceeded

---

**`check_disk() -> bool`**

Check if disk usage exceeds threshold.

**Returns:** `True` if threshold exceeded

---

**`perform_healing() -> List[str]`**

Perform auto-healing actions.

**Returns:** List of actions taken (e.g., ["cache_cleared", "logs_rotated"])

---

**`start()`**

Start the auto-healing daemon.

---

**`stop()`**

Stop the auto-healing daemon.

---

**`run()`**

Run the auto-healing daemon main loop.

### Rust API

#### CommandExecutor

Safe command execution with whitelist.

```rust
use lucy_core::CommandExecutor;

let executor = CommandExecutor::new();
let result = executor.execute("ls -la")?;
```

##### Methods

**`new() -> Self`**

Create new executor with default whitelist.

---

**`is_allowed(command: &str) -> bool`**

Check if command is allowed.

---

**`execute(command: &str) -> PyResult<String>`**

Execute command safely.

---

**`allow_command(command: String)`**

Add command to whitelist.

---

**`disallow_command(command: String)`**

Remove command from whitelist.

---

**`get_allowed_commands() -> Vec<String>`**

Get list of allowed commands.

#### SystemMonitor

System resource monitoring.

```rust
use lucy_core::SystemMonitor;

let mut monitor = SystemMonitor::new();
monitor.refresh();
let info = monitor.get_info();
```

##### Methods

**`new() -> Self`**

Create new system monitor.

---

**`refresh()`**

Refresh system information.

---

**`get_info() -> SystemInfo`**

Get current system information.

**Returns:**
```rust
SystemInfo {
    cpu_usage: f32,
    total_memory: u64,
    used_memory: u64,
    total_disk: u64,
    used_disk: u64,
    process_count: usize
}
```

---

**`get_cpu_usage() -> f32`**

Get CPU usage percentage.

---

**`get_memory_usage() -> (u64, u64)`**

Get (used, total) memory in bytes.

---

**`get_disk_usage() -> (u64, u64)`**

Get (used, total) disk in bytes.

---

**`check_memory_threshold(threshold_percent: f32) -> bool`**

Check if memory usage exceeds threshold.

**Parameters:**
- `threshold_percent`: Threshold percentage (e.g., 85.0)

**Returns:** `true` if threshold exceeded

---

**`check_disk_threshold(threshold_percent: f32) -> bool`**

Check if disk usage exceeds threshold.

**Parameters:**
- `threshold_percent`: Threshold percentage (e.g., 90.0)

**Returns:** `true` if threshold exceeded

---

**`clear_system_cache() -> PyResult<String>`**

Clear system cache safely.

**Returns:** Result message with count of cleared directories

---

**`rotate_logs(log_dir: &str, max_size_mb: u64) -> PyResult<String>`**

Rotate logs exceeding size limit.

**Parameters:**
- `log_dir`: Path to log directory
- `max_size_mb`: Maximum size in MB

**Returns:** Result message with count of rotated files

#### Logging

**`init_logging(log_dir: Option<String>)`**

Initialize structured logging with rotation.

```rust
use lucy_core::init_logging;

init_logging(Some("/var/log/lucy".to_string()))?;
```

## Desktop UI API

### Tauri Commands

#### execute_command

Execute a shell command.

**Invoke:**
```typescript
import { invoke } from "@tauri-apps/api/core";

const result = await invoke<CommandResult>("execute_command", {
  command: "ls -la"
});
```

**Parameters:**
- `command`: Shell command to execute

**Returns:**
```typescript
{
  success: boolean;
  output: string;
  error?: string;
}
```

---

#### get_system_info

Get system resource information.

**Invoke:**
```typescript
const info = await invoke<SystemInfo>("get_system_info");
```

**Returns:**
```typescript
{
  cpu_usage: number;
  total_memory: number;
  used_memory: number;
  total_disk: number;
  used_disk: number;
  process_count: number;
}
```

---

#### get_logs

Get system logs.

**Invoke:**
```typescript
const logs = await invoke<string[]>("get_logs");
```

**Returns:**
```typescript
string[]  // Array of log entries
```

---

#### agent_status

Check if agent daemon is running.

**Invoke:**
```typescript
const running = await invoke<boolean>("agent_status");
```

**Returns:**
```typescript
boolean
```

## Configuration API

### Agent Configuration

Located at `/etc/lucy/agent.conf`.

```ini
[daemon]
log_dir = /var/log/lucy
max_log_size = 100M
ipc_port = 8080
autostart = true

[safety]
require_confirmation = true
enable_whitelist = true

[ai]
model = gpt-3.5-turbo
max_tokens = 500
temperature = 0.7

# Ollama fallback
fallback_to_ollama = true
ollama_model = llama2
ollama_endpoint = http://localhost:11434

[auto_healing]
enabled = true
memory_threshold = 85
disk_threshold = 90
clear_cache = true
rotate_logs = true
max_log_size = 100M
check_interval = 300
```

### Environment Variables

- `LUCY_LOG_DIR`: Override log directory
- `LUCY_CONFIG_PATH`: Path to config file
- `LUCY_IPC_PORT`: Override IPC port

## AI-Native Terminal API

### ai-shell

Bash wrapper with natural language command translation.

**Location:** `/usr/local/bin/ai-shell`

**Usage:**
```bash
ai-shell
```

**Features:**
- Natural language to command translation
- User confirmation before execution
- Fallback to direct execution
- Color-coded output

**Example Session:**
```bash
ai-shell$ list files
Translated command: ls -la
Execute? (y/n) y
# Output of ls -la

ai-shell$ show disk usage
Translated command: df -h
Execute? (y/n) y
# Output of df -h

ai-shell$ exit
Goodbye!
```

### Shell Wrapper Python Module

**Module:** `lucy_agent.shell_wrapper`

**Usage:**
```bash
python3 -m lucy_agent.shell_wrapper "show disk usage"
# Output: df -h
```

**Returns:**
- Translated command on stdout
- "NO_TRANSLATION" on stderr if translation fails

## IPC Protocol

### WebSocket (Planned)

The daemon will expose a WebSocket interface for real-time communication.

**Endpoint:** `ws://localhost:8080`

**Message Format:**
```json
{
  "type": "command",
  "data": {
    "text": "show disk usage"
  }
}
```

**Response:**
```json
{
  "type": "response",
  "data": {
    "success": true,
    "output": "...",
    "risk_level": "safe"
  }
}
```

### HTTP API (Planned)

REST API for programmatic access.

**Endpoints:**
- `POST /api/command` - Execute command
- `GET /api/system` - Get system info
- `GET /api/logs` - Get logs
- `GET /api/status` - Get agent status

## Error Codes

### Python Errors

- `ValueError`: Invalid input
- `RuntimeError`: Execution failure
- `PermissionError`: Permission denied

### Rust Errors

- `PyValueError`: Invalid Python value
- `PyRuntimeError`: Runtime error

### Tauri Errors

- Command invocation failures
- IPC communication errors

## Rate Limiting

To prevent abuse, the following rate limits apply:

- Command execution: 10/minute
- System info queries: 60/minute
- Log retrieval: 30/minute

## Authentication

Future versions will include:

- API key authentication
- User authentication
- Role-based access control

## Examples

### Complete Example

```python
import asyncio
from lucy_agent import LucyDaemon

async def main():
    daemon = LucyDaemon()
    await daemon.start()

    # Execute command
    result = await daemon.process_command("list files")
    print(result["output"])

    # Get system info
    info = await daemon.get_system_info()
    print(f"CPU: {info['cpu_usage']}%")

    await daemon.stop()

asyncio.run(main())
```

### TypeScript Example

```typescript
import { invoke } from "@tauri-apps/api/core";

async function executeCommand(cmd: string) {
  try {
    const result = await invoke<CommandResult>("execute_command", {
      command: cmd
    });
    console.log(result.output);
  } catch (error) {
    console.error("Error:", error);
  }
}

async function getSystemInfo() {
  const info = await invoke<SystemInfo>("get_system_info");
  console.log(`CPU: ${info.cpu_usage}%`);
}
```
