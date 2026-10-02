use serde::{Deserialize, Serialize};
use std::process::Command;
use sysinfo::{System, SystemExt};
use tauri::Manager;

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

#[tauri::command]
fn get_system_info() -> SystemInfo {
    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu_usage = sys.global_cpu_usage();
    let total_memory = sys.total_memory();
    let used_memory = sys.used_memory();
    let process_count = sys.processes().len();

    let total_disk: u64 = sys.disks().iter().map(|d| d.total_space()).sum();
    let available_disk: u64 = sys.disks().iter().map(|d| d.available_space()).sum();

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
            get_system_info,
            get_logs,
            agent_status
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
