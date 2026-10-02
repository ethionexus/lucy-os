use pyo3::prelude::*;
use std::collections::HashSet;
use std::process::Command;

/// Safe command executor with whitelist validation
#[pyclass]
pub struct CommandExecutor {
    allowed_commands: HashSet<String>,
}

#[pymethods]
impl CommandExecutor {
    #[new]
    fn new() -> Self {
        let mut allowed_commands = HashSet::new();
        // Safe read-only commands
        allowed_commands.insert("ls".to_string());
        allowed_commands.insert("cat".to_string());
        allowed_commands.insert("pwd".to_string());
        allowed_commands.insert("df".to_string());
        allowed_commands.insert("free".to_string());
        allowed_commands.insert("uname".to_string());
        allowed_commands.insert("ps".to_string());
        allowed_commands.insert("top".to_string());
        allowed_commands.insert("htop".to_string());
        // Safe informational commands
        allowed_commands.insert("neofetch".to_string());
        allowed_commands.insert("pacman".to_string());

        CommandExecutor { allowed_commands }
    }

    /// Check if a command is allowed
    fn is_allowed(&self, command: &str) -> bool {
        let base_cmd = command.split_whitespace().next().unwrap_or("");
        self.allowed_commands.contains(base_cmd)
    }

    /// Execute a command safely
    fn execute(&self, command: &str) -> PyResult<String> {
        if !self.is_allowed(command) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Command not allowed: {}", command),
            ));
        }

        let output = Command::new("sh")
            .arg("-c")
            .arg(command)
            .output();

        match output {
            Ok(output) => {
                if output.status.success() {
                    Ok(String::from_utf8_lossy(&output.stdout).to_string())
                } else {
                    Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        String::from_utf8_lossy(&output.stderr).to_string(),
                    ))
                }
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                e.to_string(),
            )),
        }
    }

    /// Add a command to the whitelist
    fn allow_command(&mut self, command: String) {
        self.allowed_commands.insert(command);
    }

    /// Remove a command from the whitelist
    fn disallow_command(&mut self, command: String) {
        self.allowed_commands.remove(&command);
    }

    /// Get list of allowed commands
    fn get_allowed_commands(&self) -> Vec<String> {
        self.allowed_commands.iter().cloned().collect()
    }
}
