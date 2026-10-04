use serde::{Deserialize, Serialize};
use std::process::Command;
use sysinfo::{Disks, System};

#[derive(Debug, Serialize, Deserialize)]
struct SystemInfo {
    cpu_usage: f32,
    total_memory: u64,
    used_memory: u64,
    total_disk: u64,
    used_disk: u64,
    process_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
struct CommandResult {
    success: bool,
    output: String,
    error: Option<String>,
}

#[tauri::command]
fn execute_command(command: String) -> CommandResult {
    let output = Command::new("sh")
        .arg("-c")
        .arg(&command)
        .output();

    match output {
        Ok(output) => {
            if output.status.success() {
                CommandResult {
                    success: true,
                    output: String::from_utf8_lossy(&output.stdout).to_string(),
                    error: None,
                }
            } else {
                CommandResult {
                    success: false,
                    output: String::from_utf8_lossy(&output.stdout).to_string(),
                    error: Some(String::from_utf8_lossy(&output.stderr).to_string()),
                }
            }
        }
        Err(e) => CommandResult {
            success: false,
            output: String::new(),
            error: Some(e.to_string()),
        },
    }
}

/// Launch a GUI application by its desktop-file name (without .conf) or by
/// a raw command. Used by the dock and the app launcher.
#[tauri::command]
fn launch_app(target: String) -> CommandResult {
    // Prefer the .desktop file so the app starts with its proper
    // environment; fall back to running the target directly.
    let desktop = format!("/usr/share/applications/{}.desktop", target);
    let program = if std::path::Path::new(&desktop).exists() {
        format!("gtk-launch {}", target)
    } else {
        target.clone()
    };
    execute_command(program)
}

/// Perform a system action from the Control Center / top bar. The action is
/// mapped to a privileged system command. Privilege escalation is handled by
/// the polkit rule installed in the airootfs.
#[tauri::command]
fn system_action(action: String) -> CommandResult {
    let cmd = match action.as_str() {
        "wifi-toggle" => "nmcli radio wifi toggle",
        "wifi-status" => "nmcli radio wifi",
        "bluetooth-toggle" => "bluetoothctl power toggle",
        "bluetooth-status" => "bluetoothctl show | grep -i 'powered:'",
        "audio-toggle-mute" => "pactl set-sink-mute @DEFAULT_SINK@ toggle",
        "audio-volume-up" => "pactl set-sink-volume @DEFAULT_SINK@ +5%",
        "audio-volume-down" => "pactl set-sink-volume @DEFAULT_SINK@ -5%",
        "audio-status" => "pactl get-sink-mute @DEFAULT_SINK@",
        "vpn-start" => "systemctl start sing-box",
        "vpn-stop" => "systemctl stop sing-box",
        "vpn-status" => "systemctl is-active sing-box",
        "wallpaper-live" => "mkdir -p \"${XDG_CONFIG_HOME:-$HOME/.config}/lucy\" && echo /usr/share/lucy/lucy-wallpaper-live.mp4 > \"${XDG_CONFIG_HOME:-$HOME/.config}/lucy/wallpaper\" && pkill -f lucy-wallpaper; sleep 1; nohup lucy-wallpaper >/dev/null 2>&1 &",
        "wallpaper-launch" => "mkdir -p \"${XDG_CONFIG_HOME:-$HOME/.config}/lucy\" && echo /usr/share/lucy/lucy-launch.mp4 > \"${XDG_CONFIG_HOME:-$HOME/.config}/lucy/wallpaper\" && pkill -f lucy-wallpaper; sleep 1; nohup lucy-wallpaper >/dev/null 2>&1 &",
        "wallpaper-static" => "pkill -f lucy-wallpaper",
        _ => "",
    };
    if cmd.is_empty() {
        return CommandResult {
            success: false,
            output: String::new(),
            error: Some(format!("unknown action: {}", action)),
        };
    }
    execute_command(cmd.to_string())
}

/// Semantic search over the local offline file index.
#[tauri::command]
fn search_files(query: String, top_k: Option<u32>) -> CommandResult {
    // Delegate to the Python indexer via its JSON CLI (keeps the Tauri
    // binary free of Python/embedding dependencies).
    let k = top_k.unwrap_or(5);
    let escaped = query.replace('\'', "'\\''");
    let cmd = format!(
        "python3 -c \"from lucy_agent import search; import json; print(json.dumps(search.search_files('{}', {})))\"",
        escaped, k
    );
    execute_command(cmd)
}

/// Return the boot/rollback status from the auto-heal daemon.
#[tauri::command]
fn get_boot_status() -> CommandResult {
    let cmd = "python3 -c \"from lucy_agent import snapshot; import json; print(json.dumps(snapshot.get_boot_status()))\"".to_string();
    execute_command(cmd)
}

/// Arm an instant rollback to a Btrfs snapshot (optionally named).
#[tauri::command]
fn trigger_rollback(snapshot: Option<String>) -> CommandResult {
    let name = snapshot.unwrap_or_default();
    let escaped = name.replace('\'', "'\\''");
    let cmd = format!(
        "python3 -c \"from lucy_agent import snapshot; import json; print(json.dumps(snapshot.trigger_rollback('{}' if '{}' else None)))\"",
        escaped, escaped
    );
    execute_command(cmd)
}

/// Create a snapshot of the current root, returning its metadata.
#[tauri::command]
fn create_snapshot(name: Option<String>) -> CommandResult {
    let n = name.unwrap_or_default();
    let escaped = n.replace('\'', "'\\''");
    let cmd = format!(
        "python3 -c \"from lucy_agent import snapshot; import json; print(json.dumps(snapshot.create_snapshot('{}' if '{}' else None)))\"",
        escaped, escaped
    );
    execute_command(cmd)
}

// ---------------------------------------------------------------------------
// Week 4: optional Amharic/Ge'ez localization.
// Every one of these is opt-in. English (US) stays the system default and the
// helpers degrade to a no-op / English when the optional tooling is missing.
// ---------------------------------------------------------------------------

/// Toggle (or force) the keyboard layout: English (US) <-> Amharic/Ethiopic.
#[tauri::command]
fn keyboard_layout(action: Option<String>) -> CommandResult {
    let a = action.unwrap_or_else(|| "toggle".to_string());
    let escaped = a.replace('\'', "'\\''");
    execute_command(format!("lucy-keyboard '{}'", escaped))
}

/// Install / remove / query the optional am_ET.UTF-8 locale pack.
#[tauri::command]
fn system_locale(action: Option<String>) -> CommandResult {
    let a = action.unwrap_or_else(|| "status".to_string());
    let escaped = a.replace('\'', "'\\''");
    execute_command(format!("lucy-locale '{}'", escaped))
}

/// Toggle (or force) the optional Heritage theme accent.
#[tauri::command]
fn heritage_theme(action: Option<String>) -> CommandResult {
    let a = action.unwrap_or_else(|| "status".to_string());
    let escaped = a.replace('\'', "'\\''");
    execute_command(format!("lucy-theme '{}'", escaped))
}

/// Report the current state of every optional localization feature so the
/// Settings pane can render accurate toggle positions on mount.
#[tauri::command]
fn get_localization_status() -> CommandResult {
    execute_command(
        "printf 'keyboard=%s\\n' \"$(lucy-keyboard status 2>/dev/null)\"; \
         printf 'locale=%s\\n' \"$(lucy-locale status 2>/dev/null)\"; \
         printf 'theme=%s\\n' \"$(lucy-theme status 2>/dev/null)\"".to_string(),
    )
}

#[tauri::command]
fn get_system_info() -> SystemInfo {
    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu_usage = sys.global_cpu_info().cpu_usage();
    let total_memory = sys.total_memory();
    let used_memory = sys.used_memory();
    let process_count = sys.processes().len();

    let disks = Disks::new_with_refreshed_list();
    let total_disk: u64 = disks.list().iter().map(|d| d.total_space()).sum();
    let available_disk: u64 = disks.list().iter().map(|d| d.available_space()).sum();

    SystemInfo {
        cpu_usage,
        total_memory,
        used_memory,
        total_disk,
        used_disk: total_disk - available_disk,
        process_count,
    }
}

#[tauri::command]
fn get_logs() -> Vec<String> {
    // Placeholder for log retrieval
    vec!["Log entry 1".to_string(), "Log entry 2".to_string()]
}

#[tauri::command]
fn agent_status() -> bool {
    // Placeholder for agent status check
    true
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            execute_command,
            launch_app,
            system_action,
            search_files,
            get_boot_status,
            trigger_rollback,
            create_snapshot,
            keyboard_layout,
            system_locale,
            heritage_theme,
            get_localization_status,
            get_system_info,
            get_logs,
            agent_status
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
