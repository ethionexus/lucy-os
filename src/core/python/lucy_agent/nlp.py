"""Natural language to command translation"""

from typing import Optional, List
from pydantic import BaseModel


class CommandIntent(BaseModel):
    """Parsed command intent"""
    command: str
    confidence: float
    explanation: str


class CommandTranslator:
    """Translates natural language to bash commands"""

    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        # Initialize with simple rule-based patterns
        self.patterns = {
            "list files": "ls -la",
            "show disk usage": "df -h",
            "show memory": "free -h",
            "show processes": "ps aux",
            "system info": "uname -a",
            "current directory": "pwd",
        }

    def translate(self, text: str) -> CommandIntent:
        """Translate natural language to command"""
        text_lower = text.lower().strip()

        # Check for pattern matches
        for pattern, command in self.patterns.items():
            if pattern in text_lower:
                return CommandIntent(
                    command=command,
                    confidence=0.9,
                    explanation=f"Matched pattern: {pattern}",
                )

        # Fallback: return unknown
        return CommandIntent(
            command="",
            confidence=0.0,
            explanation="Could not translate to known command",
        )

    def add_pattern(self, pattern: str, command: str):
        """Add a new translation pattern"""
        self.patterns[pattern] = command

    def get_patterns(self) -> List[str]:
        """Get all registered patterns"""
        return list(self.patterns.keys())
