#!/bin/bash
# Functional test for the v0.4.0 Phase 1 helpers:
#   lucy-flatpak-init  (Flathub first-boot setup)
#   lucy-app-manager   (Flatpak front-end)
#
# Uses a fake `flatpak` (scripts/testdata/fake-flatpak) so it never touches a
# real system. Runs on Linux and on Git Bash/MSYS; checks that need a
# POSIX-executable flatpak are skipped with an explicit note on Windows.
#
# Usage: scripts/test-app-manager.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
FAKE_SRC="$SCRIPT_DIR/testdata/fake-flatpak"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/lucy-appmgr-XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

BIN="$REPO/src/configs/airootfs/usr/local/bin"

export PATH="$WORK/bin:$PATH"
export FAKE_FLATPAK_STATE="$WORK/flatpak-state"
export LUCY_STATE_DIR="$WORK/lucy"
export LUCY_APPS_JSON="$REPO/src/configs/airootfs/etc/lucy/apps.json"
export PYTHONPATH="$REPO/src/core/python${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONIOENCODING=utf-8

mkdir -p "$WORK/bin" "$FAKE_FLATPAK_STATE" "$LUCY_STATE_DIR"
cp -f "$FAKE_SRC" "$WORK/bin/flatpak"
chmod +x "$WORK/bin/flatpak"

fail=0
check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  OK   $label -> '$actual'"
  else
    echo "  FAIL $label -> expected '$expected', got '$actual'"
    fail=1
  fi
}

# Native Windows python cannot exec an MSYS script found via PATH. Detect that
# so the affected checks can be skipped honestly instead of failing.
PYBIN=""
for cand in python3 python; do
  command -v "$cand" >/dev/null 2>&1 && { PYBIN="$cand"; break; }
done
PY_CAN_EXEC_FAKE=0
if [ -n "$PYBIN" ] && "$PYBIN" -c "import subprocess; raise SystemExit(subprocess.run(['flatpak','--version'], capture_output=True).returncode)" >/dev/null 2>&1; then
  PY_CAN_EXEC_FAKE=1
fi

echo "=== preflight ==="
echo "  flatpak: $(command -v flatpak) ($(flatpak --version))"
echo "  python: $PYBIN (can exec fake flatpak: $PY_CAN_EXEC_FAKE)"

echo "=== lucy-flatpak-init: status before setup ==="
"$BIN/lucy-flatpak-init" --status >/dev/null 2>&1
check "status exit (not configured)" "1" "$?"

echo "=== lucy-flatpak-init: first run adds Flathub ==="
"$BIN/lucy-flatpak-init" >/dev/null 2>&1
check "first run exit" "0" "$?"
check "remote recorded" "flathub" "$(cat "$FAKE_FLATPAK_STATE/remotes")"
check "marker written" "yes" "$([ -f "$LUCY_STATE_DIR/flatpak-init.done" ] && echo yes || echo no)"

echo "=== lucy-flatpak-init: second run is idempotent ==="
out=$("$BIN/lucy-flatpak-init" 2>&1)
check "second run exit" "0" "$?"
check "still exactly one remote" "1" "$(grep -c . "$FAKE_FLATPAK_STATE/remotes")"
case "$out" in
  *"already initialised"*) echo "  OK   short-circuited on marker" ;;
  *) echo "  FAIL did not short-circuit: $out"; fail=1 ;;
esac

echo "=== lucy-flatpak-init: --status now succeeds ==="
"$BIN/lucy-flatpak-init" --status >/dev/null 2>&1
check "status exit (configured)" "0" "$?"

echo "=== lucy-flatpak-init: missing flatpak never fails the boot ==="
rm -f "$LUCY_STATE_DIR/flatpak-init.done"
out=$(PATH="/usr/bin:/bin" "$BIN/lucy-flatpak-init" 2>&1)
check "missing flatpak exit" "0" "$?"
case "$out" in
  *"not installed"*) echo "  OK   reported missing flatpak" ;;
  *) echo "  FAIL unexpected output: $out"; fail=1 ;;
esac

echo "=== lucy-app-manager: status / list ==="
"$BIN/lucy-app-manager" status >/dev/null 2>&1
check "status exit" "0" "$?"
out=$("$BIN/lucy-app-manager" list 2>/dev/null)
case "$out" in
  *org.mozilla.firefox*) echo "  OK   firefox in catalog" ;;
  *) echo "  FAIL firefox missing"; fail=1 ;;
esac

echo "=== lucy-app-manager: search ==="
out=$("$BIN/lucy-app-manager" search spotify 2>/dev/null)
echo "$out" | grep -q "com.spotify.Client" && echo "  OK   catalog hit" || { echo "  FAIL catalog hit"; fail=1; }
if [ "$PY_CAN_EXEC_FAKE" = "1" ]; then
  out_remote=$("$BIN/lucy-app-manager" search someapp 2>/dev/null)
  echo "$out_remote" | grep -q "org.example.SomeApp" && echo "  OK   flathub result merged" || { echo "  FAIL flathub merge"; fail=1; }
else
  echo "  SKIP flathub merge (native python cannot exec the MSYS fake flatpak)"
fi

echo "=== lucy-app-manager: install / list / remove ==="
if [ "$PY_CAN_EXEC_FAKE" = "1" ]; then
  "$BIN/lucy-app-manager" install com.spotify.Client >/dev/null 2>&1
  check "install exit" "0" "$?"
  check "appears in installed" "com.spotify.Client" \
    "$("$BIN/lucy-app-manager" installed 2>/dev/null | awk 'NR>2 {print $1}' | head -1)"
  "$BIN/lucy-app-manager" remove com.spotify.Client >/dev/null 2>&1
  check "remove exit" "0" "$?"
  check "gone after remove" "0" \
    "$("$BIN/lucy-app-manager" installed 2>/dev/null | grep -c 'com.spotify.Client')"
else
  echo "  SKIP install/list/remove (native python cannot exec the MSYS fake flatpak)"
fi

echo "=== lucy-app-manager: bad ref fails cleanly ==="
"$BIN/lucy-app-manager" install 'bad ref' >/dev/null 2>&1
check "bad ref exit" "1" "$?"

echo "=== lucy-app-manager: --json is machine readable ==="
out=$("$BIN/lucy-app-manager" status --json 2>/dev/null)
if printf '%s' "$out" | "$PYBIN" -c "import json,sys; d=json.load(sys.stdin); assert d['catalog_apps'] >= 20; print('  OK   json ok (catalog_apps=%s)' % d['catalog_apps'])" 2>/dev/null; then
  :
else
  echo "  FAIL bad json"; fail=1
fi

echo
if [ "$fail" -eq 0 ]; then echo "RESULT: ALL PASS"; else echo "RESULT: FAILURES"; fi
exit "$fail"
