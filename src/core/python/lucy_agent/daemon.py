"""Main daemon process for Lucy AI Agent"""

import asyncio
import json
import logging
from typing import Optional
from pathlib import Path

from .nlp import CommandTranslator
from .safety import SafetyValidator

# Import Rust module
try:
    import lucy_core
except ImportError:
    lucy_core = None
    logging.warning("lucy_core Rust module not available, running in degraded mode")


class LucyDaemon:
    """Main daemon for Lucy OS AI Agent"""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.translator = CommandTranslator(config=self.config)
        self.safety = SafetyValidator()
        self.executor = None

        if lucy_core:
            self.executor = lucy_core.CommandExecutor()
            self.monitor = lucy_core.SystemMonitor()
            lucy_core.init_logging(self.config.get("log_dir", "/var/log/lucy"))

        self.running = False
        self.logger = logging.getLogger("lucy.daemon")

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file"""
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                return json.load(f)
        return {
            "log_dir": "/var/log/lucy",
            "max_log_size": "100M",
            "ipc_port": 8080,
        }

    async def process_command(self, text: str) -> dict:
        """Process natural language command"""
        # Translate to command
        intent = self.translator.translate(text)

        if not intent.command:
            return {
                "success": False,
                "error": "Could not translate to command",
                "explanation": intent.explanation,
            }

        # Safety check
        safety = self.safety.validate(intent.command)

        if not safety.is_safe:
            return {
                "success": False,
                "error": "Command rejected for safety",
                "risk_level": safety.risk_level,
                "reason": safety.reason,
            }

        # Execute if Rust module available
        if self.executor:
            try:
                result = self.executor.execute(intent.command)
                return {
                    "success": True,
                    "command": intent.command,
                    "output": result,
                    "risk_level": safety.risk_level,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "command": intent.command,
                }
        else:
            return {
                "success": False,
                "error": "Executor not available",
                "command": intent.command,
            }

    async def get_system_info(self) -> dict:
        """Get system resource information"""
        if lucy_core and self.monitor:
            self.monitor.refresh()
            info = self.monitor.get_info()
            return {
                "cpu_usage": info.cpu_usage,
                "total_memory": info.total_memory,
                "used_memory": info.used_memory,
                "total_disk": info.total_disk,
                "used_disk": info.used_disk,
                "process_count": info.process_count,
            }
        return {"error": "System monitor not available"}

    async def start(self):
        """Start the daemon"""
        self.running = True
        self.logger.info("Lucy Daemon started")

    async def stop(self):
        """Stop the daemon"""
        self.running = False
        self.logger.info("Lucy Daemon stopped")

    async def run(self):
        """Main daemon loop"""
        await self.start()
        while self.running:
            await asyncio.sleep(1)
