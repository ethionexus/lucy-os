use pyo3::prelude::*;
use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt};
use tracing_appender::rolling;

/// Initialize structured logging with rotation
#[pyfunction]
fn init_logging(log_dir: Option<String>) -> PyResult<()> {
    let log_path = log_dir.unwrap_or_else(|| "/var/log/lucy".to_string());

    let file_appender = rolling::daily(&log_path, "lucy.log");
    let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);

    tracing_subscriber::registry()
        .with(
            fmt::layer()
                .with_writer(non_blocking)
                .with_ansi(false)
                .with_level(true)
                .with_target(true),
        )
        .with(fmt::layer().with_ansi(true))
        .init();

    Ok(())
}
