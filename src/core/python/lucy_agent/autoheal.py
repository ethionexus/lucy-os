"""Auto-healing system daemon for Lucy OS"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

# Import Rust module
try:
    import lucy_core
except ImportError:
    lucy_core = None
    logging.warning("lucy_core Rust module not available, running in degraded mode")


class AutoHealDaemon:
    """Auto-healing daemon for system resource management"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.monitor = None
        self.running = False
        self.logger = logging.getLogger("lucy.autoheal")

        if lucy_core:
            self.monitor = lucy_core.SystemMonitor()
            lucy_core.init_logging(self.config.get("log_dir", "/var/log/lucy"))

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return json.load(f)
        return {
            "log_dir": "/var/log/lucy",
            "memory_threshold": 85,
            "disk_threshold": 90,
            "clear_cache": True,
            "rotate_logs": True,
            "max_log_size": "100M",
            "check_interval": 300,
        }

    async def check_memory(self) -> bool:
        """Check if memory usage exceeds threshold"""
        if not self.monitor:
            return False

        threshold = self.config.get("memory_threshold", 85)
        exceeds = self.monitor.check_memory_threshold(threshold)

        if exceeds:
            self.logger.warning(f"Memory usage exceeds {threshold}% threshold")
            return True
        return False

    async def check_disk(self) -> bool:
        """Check if disk usage exceeds threshold"""
        if not self.monitor:
            return False

        threshold = self.config.get("disk_threshold", 90)
        exceeds = self.monitor.check_disk_threshold(threshold)

        if exceeds:
            self.logger.warning(f"Disk usage exceeds {threshold}% threshold")
            return True
        return False

    async def perform_healing(self):
        """Perform auto-healing actions"""
        actions_taken = []

        # Clear cache if enabled
        if self.config.get("clear_cache", True):
            try:
                if self.monitor:
                    result = self.monitor.clear_system_cache()
                    self.logger.info(f"Cache cleared: {result}")
                    actions_taken.append("cache_cleared")
            except Exception as e:
                self.logger.error(f"Failed to clear cache: {e}")

        # Rotate logs if enabled
        if self.config.get("rotate_logs", True):
            try:
                if self.monitor:
                    log_dir = self.config.get("log_dir", "/var/log/lucy")
                    max_size = self._parse_size(self.config.get("max_log_size", "100M"))
                    result = self.monitor.rotate_logs(log_dir, max_size)
                    self.logger.info(f"Logs rotated: {result}")
                    actions_taken.append("logs_rotated")
            except Exception as e:
                self.logger.error(f"Failed to rotate logs: {e}")

        return actions_taken

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '100M' to bytes"""
        size_str = size_str.upper()
        multipliers = {
            "B": 1,
            "K": 1024,
            "M": 1024 * 1024,
            "G": 1024 * 1024 * 1024,
        }

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                value = int(size_str[:-1])
                return value * multiplier

        return int(size_str)

    async def monitor_loop(self):
        """Main monitoring loop"""
        check_interval = self.config.get("check_interval", 300)

        while self.running:
            try:
                self.logger.info("Running auto-healing check")

                memory_exceeded = await self.check_memory()
                disk_exceeded = await self.check_disk()

                if memory_exceeded or disk_exceeded:
                    self.logger.info("Thresholds exceeded, performing healing actions")
                    actions = await self.perform_healing()
                    self.logger.info(f"Auto-healing actions taken: {actions}")

            except Exception as e:
                self.logger.error(f"Auto-healing check failed: {e}")

            await asyncio.sleep(check_interval)

    async def start(self):
        """Start the auto-healing daemon"""
        self.running = True
        self.logger.info("Auto-healing daemon started")

    async def stop(self):
        """Stop the auto-healing daemon"""
        self.running = False
        self.logger.info("Auto-healing daemon stopped")

    async def run(self):
        """Run the auto-healing daemon"""
        await self.start()
        await self.monitor_loop()


async def main():
    """Main entry point"""
    daemon = AutoHealDaemon(config_path="/etc/lucy/agent.conf")
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
