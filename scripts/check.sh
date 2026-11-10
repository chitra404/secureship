#!/usr/bin/env bash
# Run every check you can BEFORE pushing to GitHub.
# Needs only Python. Docker, Trivy and Syft checks run if those tools are installed.
# Usage: ./scripts/check.sh
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

IMAGE="secureship-api:check"
PORT=18000
PASS=0; FAIL=0; SKIP=0

if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY="${PYTHON:-python3}"; fi

run() {   # run "<name>" <command...>
  local name=$1; shift
  printf '%-34s' "-> $name"
  local out
  if out=$("$@" 2>&1); then
    echo "PASS"; PASS=$((PASS + 1))
  else
    echo "FAIL"; FAIL=$((FAIL + 1))
    printf '%s\n' "$out" | tail -15 | sed 's/^/     /'
  fi
}

skip() { printf '%-34s%s\n' "-> $1" "SKIP ($2)"; SKIP=$((SKIP + 1)); }

check_nonroot() {
  [ "$(docker run --rm --entrypoint id "$IMAGE" -u)" = "10001" ]
}

check_container_health() {
  local cid ok=1
  cid=$(docker run -d --rm -p "$PORT:8000" --read-only --cap-drop ALL \
        --security-opt no-new-privileges "$IMAGE") || return 1
  for _ in $(seq 1 15); do
    if "$PY" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/health', timeout=2)" 2>/dev/null; then
      ok=0; break
    fi
    sleep 1
  done
  docker stop "$cid" >/dev/null 2>&1 || true
  return $ok
}

echo "SecureShip pre-push checks"
echo "--------------------------"

run "Unit tests (pytest)" "$PY" -m pytest -q

DOCKER_OK=0
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  run "Docker build" docker build -q -t "$IMAGE" .
  if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    DOCKER_OK=1
    run "Container runs as non-root" check_nonroot
    run "Container health (hardened run)" check_container_health
  fi
else
  skip "Docker checks" "Docker not running"
fi

if [ "$DOCKER_OK" -eq 1 ] && command -v trivy >/dev/null 2>&1; then
  run "Trivy gate (fixable CRITICAL)" trivy image --quiet --severity CRITICAL --ignore-unfixed --exit-code 1 "$IMAGE"
else
  skip "Trivy gate" "trivy or image missing"
fi

if [ "$DOCKER_OK" -eq 1 ] && command -v syft >/dev/null 2>&1; then
  run "SBOM generation (Syft)" syft "$IMAGE" -q -o spdx-json=sbom.spdx.json
else
  skip "SBOM generation" "syft or image missing"
fi

echo "--------------------------"
echo "Passed: $PASS   Failed: $FAIL   Skipped: $SKIP"
[ "$FAIL" -eq 0 ]
