"""Tests for the optional multi-language AI directive (`/lang:xx`).

English is the default. These directives are strictly opt-in, and a malformed
or unsupported code must never break an otherwise valid command.
"""

import pytest

from lucy_agent.nlp import (
    SUPPORTED_AI_LANGUAGES,
    CommandTranslator,
    parse_language_flag,
)


@pytest.mark.parametrize(
    "text,expected_clean,expected_lang",
    [
        # No directive -> input is returned untouched.
        ("list files", "list files", None),
        ("", "", None),
        # Leading directive is stripped.
        ("/lang:am show disk usage", "show disk usage", "am"),
        # Trailing directive is stripped too.
        ("show processes /lang:am", "show processes", "am"),
        # Explicit English is honoured (and still stripped).
        ("/lang:en show memory", "show memory", "en"),
        # Case is normalised.
        ("/LANG:AM system info", "system info", "am"),
        # Unknown code is stripped but ignored rather than raising.
        ("/lang:xx current directory", "current directory", None),
        ("/lang: current directory", "/lang: current directory", None),
    ],
)
def test_parse_language_flag(text, expected_clean, expected_lang):
    clean, lang = parse_language_flag(text)
    assert clean == expected_clean
    assert lang == expected_lang


def test_english_is_in_supported_languages():
    assert "en" in SUPPORTED_AI_LANGUAGES


def test_translate_still_matches_patterns_with_directive():
    """The directive must not interfere with pattern matching."""
    tr = CommandTranslator(config={"fallback_to_ollama": False})
    intent = tr.translate("/lang:am show disk usage")
    assert intent.command == "df -h"
    assert intent.confidence > 0.5


def test_default_language_is_english():
    tr = CommandTranslator(config={})
    assert tr.default_language == "en"


def test_default_language_can_be_overridden_by_config():
    tr = CommandTranslator(config={"ai_language": "am"})
    assert tr.default_language == "am"


def test_unsupported_directive_does_not_break_translation():
    """A typo in the directive falls back to normal English behaviour."""
    tr = CommandTranslator(config={"fallback_to_ollama": False})
    intent = tr.translate("/lang:zz list files")
    assert intent.command == "ls -la"
