use pyo3::prelude::*;
use serde::Serialize;
use sysinfo::{System, SystemExt, CpuExt, DiskExt, ProcessExt};

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
}
