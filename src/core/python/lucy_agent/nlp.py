"""Natural language to command translation"""

from typing import Optional, List, Tuple
from pydantic import BaseModel
import socket
import re
import requests


class CommandIntent(BaseModel):
    """Parsed command intent"""
    command: str
    confidence: float
    explanation: str


# Optional AI multi-language directive: /lang:am, /lang:en, /lang:fr, ...
# English remains the default; the directive is strictly opt-in.
# The directive word is matched case-insensitively so /Lang:am works too.
_LANG_FLAG_RE = re.compile(r"/lang:([a-z]{2,5})\b", re.IGNORECASE)
SUPPORTED_AI_LANGUAGES = {"en", "am", "fr", "ar", "es", "zh", "ru"}


def parse_language_flag(text: str) -> Tuple[str, Optional[str]]:
    """Strip an optional /lang:xx directive from text.

    Returns (clean_text, language_code or None). Unknown language codes are
    treated as absent so behaviour is unchanged for normal commands.
    """
    m = _LANG_FLAG_RE.search(text)
    if not m:
        return text, None
    lang = m.group(1).lower()
    clean = _LANG_FLAG_RE.sub("", text).strip()
    if lang not in SUPPORTED_AI_LANGUAGES:
        return clean, None
    return clean, lang


class CommandTranslator:
    """Translates natural language to bash commands"""

    def __init__(self, model: str = "gpt-3.5-turbo", config: dict = None):
        self.model = model
        self.config = config or {}
        self.default_language = self.config.get("ai_language", "en")
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

    def translate_with_ollama(self, text: str, language: Optional[str] = None) -> CommandIntent:
        """Translate using local Ollama when offline"""
        try:
            ollama_endpoint = self.config.get("ollama_endpoint", "http://localhost:11434")
            ollama_model = self.config.get("ollama_model", "llama2")
            lang = language or self.default_language
            lang_note = "" if lang == "en" else (
                f" The user wrote in '{lang}'; still return a shell command."
            )

            response = requests.post(
                f"{ollama_endpoint}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": f"Translate this natural language to a bash command: {text}.{lang_note} Return only the command.",
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
                        explanation=f"Translated with local Ollama ({lang})",
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
        # Optional opt-in AI language directive, e.g. "/lang:am show disk".
        text, language = parse_language_flag(text)
        text_lower = text.lower().strip()

        # Check for pattern matches first (language-independent commands).
        for pattern, command in self.patterns.items():
            if pattern in text_lower:
                return CommandIntent(
                    command=command,
                    confidence=0.9,
                    explanation=f"Matched pattern: {pattern}",
                )

        # Check if Ollama fallback is enabled and offline
        if self.config.get("fallback_to_ollama", False) and not self.has_internet():
            ollama_result = self.translate_with_ollama(text, language)
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
