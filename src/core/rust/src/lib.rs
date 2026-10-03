use pyo3::prelude::*;

mod command;
mod resource;
mod log;

/// Lucy Core - PyO3 module for AI agent
#[pymodule]
fn lucy_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<command::CommandExecutor>()?;
    m.add_class::<resource::SystemMonitor>()?;
    m.add_function(wrap_pyfunction!(log::init_logging, m)?)?;
    Ok(())
}
