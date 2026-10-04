"""Lucy OS AI Agent Daemon.

Exports are resolved lazily (PEP 562) so that importing a single, light
submodule — for example :mod:`lucy_agent.appstore`, which is pure-stdlib —
does not drag in the heavy AI dependencies (pydantic, requests, psutil).

That matters for the command-line helpers: ``lucy-app-manager`` must work
even when the AI stack is not fully installed.
"""

import importlib
from typing import Dict, Tuple

__version__ = "0.1.0"

#: public name -> (submodule suffix, attribute name in that module)
_LAZY: Dict[str, Tuple[str, str]] = {
    # nlp
    "CommandTranslator": (".nlp", "CommandTranslator"),
    # safety
    "SafetyValidator": (".safety", "SafetyValidator"),
    # daemon
    "LucyDaemon": (".daemon", "LucyDaemon"),
    # autoheal
    "AutoHealDaemon": (".autoheal", "AutoHealDaemon"),
    # models
    "init": (".models", "init"),
    "get_profile": (".models", "get_profile"),
    "get_model_spec": (".models", "get_model_spec"),
    "is_light_profile": (".models", "is_light_profile"),
    "is_high_profile": (".models", "is_high_profile"),
    # search
    "SemanticIndexer": (".search", "SemanticIndexer"),
    "search_files": (".search", "search_files"),
    "get_indexer": (".search", "get_indexer"),
    # snapshot
    "SnapshotManager": (".snapshot", "SnapshotManager"),
    "BootGuard": (".snapshot", "BootGuard"),
    "trigger_rollback": (".snapshot", "trigger_rollback"),
    "get_boot_status": (".snapshot", "get_boot_status"),
    # appstore (v0.4.0 Phase 1)
    "AppEntry": (".appstore", "AppEntry"),
    "Catalog": (".appstore", "Catalog"),
    "load_catalog": (".appstore", "load_catalog"),
    "add_flathub": (".appstore", "add_flathub"),
    "app_search": (".appstore", "search"),
    "app_install": (".appstore", "install"),
    "app_remove": (".appstore", "remove"),
    "app_list_installed": (".appstore", "list_installed"),
    "app_status": (".appstore", "status"),
}

__all__ = [
    "CommandTranslator",
    "SafetyValidator",
    "LucyDaemon",
    "AutoHealDaemon",
    "init",
    "get_profile",
    "get_model_spec",
    "is_light_profile",
    "is_high_profile",
    "SemanticIndexer",
    "search_files",
    "get_indexer",
    "SnapshotManager",
    "BootGuard",
    "trigger_rollback",
    "get_boot_status",
    "AppEntry",
    "Catalog",
    "load_catalog",
    "add_flathub",
    "app_search",
    "app_install",
    "app_remove",
    "app_list_installed",
    "app_status",
]


def __getattr__(name: str):
    """Resolve a public export on first access (PEP 562)."""
    entry = _LAZY.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = entry
    module = importlib.import_module(module_name, __name__)
    return getattr(module, attribute)


def __dir__():
    return sorted(set(__all__) | {"__version__"})
