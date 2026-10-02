"""Shell wrapper for AI-native terminal"""

import sys
import json
from pathlib import Path

# Import lucy_agent components
try:
    from lucy_agent import CommandTranslator, SafetyValidator
except ImportError:
    print("NO_TRANSLATION", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point for shell wrapper"""
    if len(sys.argv) < 2:
        print("NO_TRANSLATION", file=sys.stderr)
        sys.exit(1)

    input_text = sys.argv[1]

    # Load configuration
    config_path = Path("/etc/lucy/agent.conf")
    config = {}
    if config_path.exists():
        try:
            with open(config_path) as f:
                # Simple config parsing (not full INI parser)
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()
        except Exception:
            pass

    # Initialize translator
    translator = CommandTranslator(config=config)

    # Translate input
    intent = translator.translate(input_text)

    # If translation succeeded, return command
    if intent.command and intent.confidence > 0.5:
        print(intent.command)
    else:
        print("NO_TRANSLATION", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
