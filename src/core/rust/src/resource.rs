use pyo3::prelude::*;
use serde::Serialize;
use sysinfo::{System, SystemExt, CpuExt, DiskExt, ProcessExt};
use std::fs;
use std::path::Path;

#[derive(Serialize)]
#[pyclass]
pub struct SystemInfo {
    #[pyo3(get)]
    cpu_usage: f32,
    #[pyo3(get)]
    total_memory: u64,
    #[pyo3(get)]
    used_memory: u64,
    #[pyo3(get)]
    total_disk: u64,
    #[pyo3(get)]
    used_disk: u64,
    #[pyo3(get)]
    process_count: usize,
}

#[pymethods]
impl SystemInfo {
    fn __repr__(&self) -> String {
        format!(
            "SystemInfo(cpu: {:.1}%, mem: {}/{}, disk: {}/{}, procs: {})",
            self.cpu_usage,
            self.used_memory,
            self.total_memory,
            self.used_disk,
            self.total_disk,
            self.process_count
        )
    }
}

/// System resource monitor
#[pyclass]
pub struct SystemMonitor {
    system: System,
}

#[pymethods]
impl SystemMonitor {
    #[new]
    fn new() -> Self {
        let mut system = System::new_all();
        system.refresh_all();
        SystemMonitor { system }
    }

    /// Refresh system information
    fn refresh(&mut self) {
        self.system.refresh_all();
    }

    /// Get current system information
    fn get_info(&self) -> SystemInfo {
        let cpu_usage = self.system.global_cpu_usage();
        let total_memory = self.system.total_memory();
        let used_memory = self.system.used_memory();
        let process_count = self.system.processes().len();

        let total_disk = self.system.disks().iter().map(|d| d.total_space()).sum();
        let used_disk = self.system.disks().iter().map(|d| d.available_space()).sum();

        SystemInfo {
            cpu_usage,
            total_memory,
            used_memory,
            total_disk,
            used_disk: total_disk - used_disk,
            process_count,
        }
    }

    /// Get CPU usage percentage
    fn get_cpu_usage(&self) -> f32 {
        self.system.global_cpu_usage()
    }

    /// Get memory usage in bytes
    fn get_memory_usage(&self) -> (u64, u64) {
        (self.system.used_memory(), self.system.total_memory())
    }

    /// Get disk usage in bytes
    fn get_disk_usage(&self) -> (u64, u64) {
        let total: u64 = self.system.disks().iter().map(|d| d.total_space()).sum();
        let available: u64 = self.system.disks().iter().map(|d| d.available_space()).sum();
        (total - available, total)
    }

    /// Check if memory usage exceeds threshold
    fn check_memory_threshold(&self, threshold_percent: f32) -> bool {
        let (used, total) = self.get_memory_usage();
        let used_percent = (used as f32 / total as f32) * 100.0;
        used_percent >= threshold_percent
    }

    /// Check if disk usage exceeds threshold
    fn check_disk_threshold(&self, threshold_percent: f32) -> bool {
        let (used, total) = self.get_disk_usage();
        let used_percent = (used as f32 / total as f32) * 100.0;
        used_percent >= threshold_percent
    }

    /// Clear system cache safely
    fn clear_system_cache(&self) -> PyResult<String> {
        let paths_to_clear = vec![
            "/var/cache",
            "/tmp",
        ];

        let mut cleared = 0;
        for path in paths_to_clear {
            if Path::new(path).exists() {
                // Only clear safe directories
                if path == "/tmp" {
                    if let Err(e) = fs::remove_dir_all(path) {
                        if e.kind() != std::io::ErrorKind::NotFound {
                            return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                                format!("Failed to clear {}: {}", path, e),
                            ));
                        }
                    }
                    fs::create_dir_all(path).map_err(|e| {
                        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                            format!("Failed to recreate {}: {}", path, e),
                        )
                    })?;
                    cleared += 1;
                }
            }
        }

        Ok(format!("Cleared {} cache directories", cleared))
    }

    /// Rotate logs in specified directory
    fn rotate_logs(&self, log_dir: &str, max_size_mb: u64) -> PyResult<String> {
        let log_path = Path::new(log_dir);
        if !log_path.exists() {
            return Ok("Log directory does not exist".to_string());
        }

        let max_size_bytes = max_size_mb * 1024 * 1024;
        let mut rotated = 0;

        if let Ok(entries) = fs::read_dir(log_path) {
            for entry in entries.flatten() {
                if let Ok(metadata) = entry.metadata() {
                    if metadata.len() > max_size_bytes {
                        let file_path = entry.path();
                        let new_path = format!("{}.old", file_path.display());
                        fs::rename(&file_path, &new_path).map_err(|e| {
                            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                                format!("Failed to rotate log {}: {}", file_path.display(), e),
                            )
                        })?;
                        rotated += 1;
                    }
                }
            }
        }

        Ok(format!("Rotated {} log files", rotated))
    }
}
