"""Guard the lazy (PEP 562) export surface of the lucy_agent package.

Two properties matter:

1. Every name advertised in ``__all__`` actually resolves.
2. Importing a light submodule does *not* pull in the heavy AI dependencies.
   This is what lets ``lucy-app-manager`` run on a system where the AI stack
   is not fully installed.
"""

import subprocess
import sys
import textwrap

import lucy_agent


def test_all_names_resolve():
    """Each advertised export must be importable and non-None."""
    missing = []
    for name in lucy_agent.__all__:
        try:
            value = getattr(lucy_agent, name)
        except Exception as exc:  # pragma: no cover - reported below
            missing.append(f"{name}: {exc!r}")
            continue
        if value is None:
            missing.append(f"{name}: resolved to None")
    assert not missing, "unresolved exports: " + "; ".join(missing)


def test_unknown_attribute_raises():
    try:
        lucy_agent.definitely_not_a_real_name
    except AttributeError:
        return
    raise AssertionError("expected AttributeError for an unknown export")


def test_dir_lists_exports():
    listing = dir(lucy_agent)
    for name in lucy_agent.__all__:
        assert name in listing


def test_appstore_imports_without_pydantic():
    """appstore must import even when pydantic is unavailable.

    Run in a subprocess with the AI dependencies hidden, so the check is
    honest about what the light helper actually needs.
    """
    code = textwrap.dedent(
        """
        import sys

        # Simulate a host without the heavy AI dependencies.
        for blocked in ("pydantic", "requests", "psutil"):
            sys.modules[blocked] = None

        import lucy_agent.appstore as appstore
        assert appstore.FLATHUB_REMOTE_NAME == "flathub"
        catalog = appstore.load_catalog()
        assert catalog.apps, "catalog should not be empty"
        print("APPSTORE_STDLIB_ONLY_OK")
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "APPSTORE_STDLIB_ONLY_OK" in proc.stdout
