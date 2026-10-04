"""Tests for the Lucy App Manager (Flatpak/Flathub) — v0.4.0 Phase 1.

Nothing here executes flatpak: every system call goes through a fake runner,
so the suite runs on a bare build host and asserts on exact command lines.
"""

import json
from pathlib import Path

import pytest

from lucy_agent import appstore
from lucy_agent.appstore import (
    AppEntry,
    Catalog,
    parse_catalog,
    parse_installed,
    parse_search,
)


# --- Catalog loading -------------------------------------------------------


def test_repo_catalog_file_exists_and_parses():
    """The shipped /etc/lucy/apps.json must be valid and well-formed."""
    path = appstore.find_catalog_path()
    assert path is not None, "no apps.json found in the repository"
    assert path.name == "apps.json"
    catalog = appstore.load_catalog(path)
    assert catalog.version >= 1
    assert catalog.remote_name == "flathub"
    assert catalog.remote_url.startswith("https://")
    assert len(catalog.apps) >= 20


def test_shipped_catalog_has_core_native_apps():
    catalog = appstore.load_catalog()
    core = catalog.core_apps()
    assert core, "catalog should declare at least one core app"
    # Core apps are the pre-installed ones, so they must be native packages.
    for app in core:
        assert app.kind == "native", f"{app.id} is core but not native"
        assert app.native_package, f"{app.id} is missing native_package"


def test_shipped_catalog_is_valid_json():
    path = appstore.find_catalog_path()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    assert data["remote_name"] == "flathub"
    assert isinstance(data["apps"], list)


# --- Catalog model ---------------------------------------------------------


def test_parse_catalog_minimal():
    catalog = parse_catalog(
        {
            "version": 2,
            "apps": [
                {"id": "org.example.App", "name": "Example", "category": "utility"}
            ],
        }
    )
    assert catalog.version == 2
    assert len(catalog.apps) == 1
    assert catalog.apps[0].is_flatpak


def test_parse_catalog_rejects_missing_id():
    with pytest.raises(ValueError):
        parse_catalog({"apps": [{"name": "No id"}]})


def test_parse_catalog_rejects_duplicate_ids():
    with pytest.raises(ValueError):
        parse_catalog(
            {"apps": [{"id": "a.b"}, {"id": "a.b"}]}
        )


def test_parse_catalog_rejects_native_without_package():
    with pytest.raises(ValueError):
        parse_catalog({"apps": [{"id": "a.b", "kind": "native"}]})


def test_parse_catalog_rejects_unknown_kind():
    with pytest.raises(ValueError):
        parse_catalog({"apps": [{"id": "a.b", "kind": "snap"}]})


def test_parse_catalog_rejects_non_list_apps():
    with pytest.raises(ValueError):
        parse_catalog({"apps": {"id": "a.b"}})


def test_catalog_get_and_find():
    catalog = Catalog(
        version=1,
        apps=[
            AppEntry("org.mozilla.firefox", "Firefox", "browser"),
            AppEntry("com.spotify.Client", "Spotify", "media"),
        ],
    )
    assert catalog.get("com.spotify.Client").name == "Spotify"
    assert catalog.get("nope") is None
    assert [a.id for a in catalog.find("fire")] == ["org.mozilla.firefox"]
    assert len(catalog.find("")) == 2


def test_catalog_categories_are_unique_and_ordered():
    catalog = Catalog(
        version=1,
        apps=[
            AppEntry("a", "A", "browser"),
            AppEntry("b", "B", "media"),
            AppEntry("c", "C", "browser"),
        ],
    )
    assert catalog.categories() == ["browser", "media"]


# --- Lightweight parser: no bash invocation needed -------------------------


class FakeRunner:
    """Records commands and returns scripted output."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, args, timeout=300):
        args = list(args)
        self.calls.append(args)
        key = " ".join(args)
        for pattern, value in self.responses.items():
            if pattern in key:
                return value
        return (0, "", "")

    def ran(self, needle):
        return any(needle in " ".join(c) for c in self.calls)


# --- Flatpak command construction -----------------------------------------


def test_flatpak_available_true_when_version_succeeds():
    runner = FakeRunner({"flatpak --version": (0, "Flatpak 1.18.4\n", "")})
    assert appstore.flatpak_available(runner) is True


def test_flatpak_available_false_when_missing():
    runner = FakeRunner({"flatpak --version": (127, "", "not found")})
    assert appstore.flatpak_available(runner) is False


def test_default_runner_reports_missing_binary_without_raising():
    code, out, err = appstore.default_runner(["definitely-not-a-real-binary-xyz"])
    assert code == 127
    assert "not found" in err


def test_list_remotes_parses_columns():
    runner = FakeRunner({"flatpak remotes": (0, "flathub\nflathub-beta\n", "")})
    assert appstore.list_remotes(runner) == ["flathub", "flathub-beta"]


def test_list_remotes_skips_header_and_blank_lines():
    runner = FakeRunner({"flatpak remotes": (0, "name\n\nflathub\n", "")})
    assert appstore.list_remotes(runner) == ["flathub"]


def test_flathub_configured_true_and_false():
    yes = FakeRunner({"flatpak remotes": (0, "flathub\n", "")})
    no = FakeRunner({"flatpak remotes": (0, "someother\n", "")})
    assert appstore.flathub_configured(yes) is True
    assert appstore.flathub_configured(no) is False


def test_add_flathub_uses_if_not_exists_and_system():
    runner = FakeRunner()
    appstore.add_flathub(runner=runner)
    assert runner.calls == [
        [
            "flatpak",
            "remote-add",
            "--if-not-exists",
            "--system",
            "flathub",
            "https://dl.flathub.org/repo/flathub.flatpakrepo",
        ]
    ]


def test_add_flathub_custom_remote():
    runner = FakeRunner()
    appstore.add_flathub(remote_name="myremote", url="https://x/y.flatpakrepo",
                         runner=runner, system=False)
    assert runner.calls[0][:3] == ["flatpak", "remote-add", "--if-not-exists"]
    assert runner.calls[0][-2:] == ["myremote", "https://x/y.flatpakrepo"]


def test_install_command_is_noninteractive_by_default():
    runner = FakeRunner()
    appstore.install("com.spotify.Client", runner=runner)
    assert runner.calls == [
        ["flatpak", "install", "--system", "-y", "flathub", "com.spotify.Client"]
    ]


def test_install_rejects_whitespace_ref():
    with pytest.raises(ValueError):
        appstore.install("bad app id")


def test_install_rejects_empty_ref():
    with pytest.raises(ValueError):
        appstore.install("")


def test_remove_command():
    runner = FakeRunner()
    appstore.remove("org.gimp.GIMP", runner=runner)
    assert runner.calls == [
        ["flatpak", "uninstall", "--system", "-y", "org.gimp.GIMP"]
    ]


def test_update_command():
    runner = FakeRunner()
    appstore.update(runner=runner)
    assert runner.calls == [["flatpak", "update", "--system", "-y"]]


# --- Output parsing --------------------------------------------------------


def test_parse_installed_tab_separated():
    out = (
        "org.mozilla.firefox\tFirefox\t157.0\tstable\tflathub\n"
        "com.spotify.Client\tSpotify\t1.2\tstable\tflathub\n"
    )
    rows = parse_installed(out)
    assert len(rows) == 2
    assert rows[0]["application"] == "org.mozilla.firefox"
    assert rows[0]["origin"] == "flathub"
    assert rows[1]["name"] == "Spotify"


def test_parse_installed_ignores_blank_lines():
    assert parse_installed("\n   \n") == []


def test_parse_installed_tolerates_missing_trailing_columns():
    rows = parse_installed("org.example.App\tExample\n")
    assert rows[0]["application"] == "org.example.App"
    assert rows[0]["version"] == ""


def test_parse_search_tab_separated():
    out = "Spotify\tcom.spotify.Client\t1.2\tMusic for everyone\n"
    rows = parse_search(out)
    assert rows[0]["application"] == "com.spotify.Client"
    assert rows[0]["description"] == "Music for everyone"


def test_search_merges_catalog_first_and_dedupes(monkeypatch):
    monkeypatch.setattr(
        appstore,
        "load_catalog",
        lambda: Catalog(
            version=1,
            apps=[AppEntry("org.mozilla.firefox", "Firefox", "browser")],
        ),
    )
    runner = FakeRunner(
        {
            "flatpak search": (
                0,
                "Firefox\torg.mozilla.firefox\t157.0\tBrowser\n"
                "Firefox Dev\torg.mozilla.firefoxdeveloperedition\t1\tDev\n",
                "",
            )
        }
    )
    results = appstore.search("fire", runner=runner)
    ids = [r["id"] for r in results]
    assert ids[0] == "org.mozilla.firefox"       # catalog hit first
    assert ids.count("org.mozilla.firefox") == 1  # de-duplicated
    assert "org.mozilla.firefoxdeveloperedition" in ids


def test_search_survives_flatpak_failure(monkeypatch):
    monkeypatch.setattr(
        appstore,
        "load_catalog",
        lambda: Catalog(version=1, apps=[AppEntry("org.mozilla.firefox", "Firefox", "browser")]),
    )
    runner = FakeRunner({"flatpak search": (1, "", "boom")})
    results = appstore.search("fire", runner=runner)
    assert [r["id"] for r in results] == ["org.mozilla.firefox"]


# --- Status ----------------------------------------------------------------


def test_status_reports_readiness(monkeypatch):
    monkeypatch.setattr(
        appstore,
        "load_catalog",
        lambda: Catalog(version=1, apps=[AppEntry("org.mozilla.firefox", "Firefox", "browser", core=True)]),
    )
    runner = FakeRunner(
        {
            "flatpak --version": (0, "Flatpak 1.18.4\n", ""),
            "flatpak remotes": (0, "flathub\n", ""),
            "flatpak list": (0, "org.mozilla.firefox\tFirefox\t1\tstable\tflathub\n", ""),
        }
    )
    info = appstore.status(runner)
    assert info["flatpak_installed"] is True
    assert info["flathub_configured"] is True
    assert info["installed"] == 1
    assert info["core_apps"] == ["org.mozilla.firefox"]


def test_status_when_flatpak_absent(monkeypatch):
    monkeypatch.setattr(
        appstore, "load_catalog", lambda: Catalog(version=1, apps=[])
    )
    runner = FakeRunner({"flatpak --version": (127, "", "missing")})
    info = appstore.status(runner)
    assert info["flatpak_installed"] is False
    assert info["flathub_configured"] is False
    assert info["installed"] == 0


# --- CLI -------------------------------------------------------------------


def test_cli_help_exits_zero(capsys):
    assert appstore.main(["help"]) == 0
    assert "Commands" in capsys.readouterr().out


def test_cli_list_json(capsys):
    assert appstore.main(["list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["remote_name"] == "flathub"
    assert len(payload["apps"]) >= 20


def test_cli_search_json(capsys, monkeypatch):
    monkeypatch.setattr(
        appstore,
        "search",
        lambda q, **kw: [{"id": "com.spotify.Client", "name": "Spotify"}],
    )
    assert appstore.main(["search", "spotify", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "spotify"
    assert payload["results"][0]["id"] == "com.spotify.Client"


def test_cli_install_json_reports_failure(capsys, monkeypatch):
    monkeypatch.setattr(
        appstore, "install", lambda app_id, **kw: (1, "", "network unreachable")
    )
    code = appstore.main(["install", "com.spotify.Client", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["exit_code"] == 1


def test_cli_install_json_reports_success(capsys, monkeypatch):
    monkeypatch.setattr(
        appstore, "install", lambda app_id, **kw: (0, "installed", "")
    )
    code = appstore.main(["install", "com.spotify.Client", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["app"] == "com.spotify.Client"


def test_cli_unknown_command_exits_two(capsys):
    assert appstore.main(["frobnicate"]) == 2


def test_cli_invalid_ref_is_reported_not_raised(capsys):
    # A bad ref raises ValueError internally; the CLI must convert it to a
    # clean exit code and JSON error rather than a traceback.
    code = appstore.main(["install", "bad ref", "--json"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
