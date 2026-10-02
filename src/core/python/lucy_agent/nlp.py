"""Natural language to command translation"""

from typing import Optional, List
from pydantic import BaseModel
import socket
import requests


class CommandIntent(BaseModel):
    """Parsed command intent"""
    command: str
    confidence: float
    explanation: str


class CommandTranslator:
    """Translates natural language to bash commands"""

    def __init__(self, model: str = "gpt-3.5-turbo", config: dict = None):
        self.model = model
        self.config = config or {}
        # Initialize with simple rule-based patterns
        self.patterns = {
            "list files": "ls -la",
            "show disk usage": "df -h",
            "show memory": "free -h",
            "show processes": "ps aux",
            "system info": "uname -a",
            "current directory": "pwd",
        }

    def has_internet(self) -> bool:
        """Check if internet connection is available"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def translate_with_ollama(self, text: str) -> CommandIntent:
        """Translate using local Ollama when offline"""
        try:
            ollama_endpoint = self.config.get("ollama_endpoint", "http://localhost:11434")
            ollama_model = self.config.get("ollama_model", "llama2")

            response = requests.post(
                f"{ollama_endpoint}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": f"Translate this natural language to a bash command: {text}. Return only the command.",
                    "stream": False,
                },
                timeout=10,
            )

            if response.status_code == 200:
                command = response.json().get("response", "").strip()
                if command:
                    return CommandIntent(
                        command=command,
                        confidence=0.7,
                        explanation="Translated with local Ollama",
                    )
        except Exception as e:
            print(f"Ollama translation failed: {e}")

        return CommandIntent(
            command="",
            confidence=0.0,
            explanation="Ollama translation failed",
        )

    def translate(self, text: str) -> CommandIntent:
        """Translate natural language to command"""
        text_lower = text.lower().strip()

        # Check for pattern matches first
        for pattern, command in self.patterns.items():
            if pattern in text_lower:
                return CommandIntent(
                    command=command,
                    confidence=0.9,
                    explanation=f"Matched pattern: {pattern}",
                )

        # Check if Ollama fallback is enabled and offline
        if self.config.get("fallback_to_ollama", False) and not self.has_internet():
            ollama_result = self.translate_with_ollama(text)
            if ollama_result.command:
                return ollama_result

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
