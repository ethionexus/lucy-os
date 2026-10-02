"""Command safety validation layer"""

from typing import List, Tuple
from pydantic import BaseModel


class SafetyCheck(BaseModel):
    """Result of safety check"""
    is_safe: bool
    risk_level: str  # "safe", "low", "medium", "high", "critical"
    reason: str
    requires_confirmation: bool


class SafetyValidator:
    """Validates commands for safety before execution"""

    def __init__(self):
        # Dangerous patterns that require confirmation
        self.dangerous_patterns = [
            "rm -rf /",
            "rm -rf /*",
            "mkfs",
            "dd if=",
            ":(){:|:&};:",
            "chmod 777",
            "chown -R",
            "shutdown",
            "reboot",
            "poweroff",
        ]

        # Read-only safe commands
        self.safe_commands = [
            "ls",
            "cat",
            "pwd",
            "df",
            "free",
            "uname",
            "ps",
            "top",
            "neofetch",
            "pacman -Q",
            "pacman -Qi",
        ]

    def validate(self, command: str) -> SafetyCheck:
        """Validate a command for safety"""
        cmd_lower = command.lower()

        # Check for critical danger
        for pattern in self.dangerous_patterns:
            if pattern in cmd_lower:
                return SafetyCheck(
                    is_safe=False,
                    risk_level="critical",
                    reason=f"Contains dangerous pattern: {pattern}",
                    requires_confirmation=True,
                )

        # Check if it's a read-only safe command
        base_cmd = command.split()[0] if command.split() else ""
        if base_cmd in self.safe_commands:
            return SafetyCheck(
                is_safe=True,
                risk_level="safe",
                reason="Read-only informational command",
                requires_confirmation=False,
            )

        # Default: medium risk, requires confirmation
        return SafetyCheck(
            is_safe=True,
            risk_level="medium",
            reason="Unknown command, requires user confirmation",
            requires_confirmation=True,
        )

    def add_dangerous_pattern(self, pattern: str):
        """Add a dangerous pattern"""
        self.dangerous_patterns.append(pattern)

    def add_safe_command(self, command: str):
        """Add a safe command"""
        self.safe_commands.append(command)
