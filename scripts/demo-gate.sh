#!/usr/bin/env bash
# Prove the Trivy release gate works, using a throwaway branch (main is never changed).
#   ./scripts/demo-gate.sh start     -> create + push a branch with a vulnerable dependency
#   ./scripts/demo-gate.sh cleanup   -> delete that branch (add --yes to skip the question)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

BRANCH="demo/vulnerable-dependency"
BAD_PACKAGE="django==2.2.0"   # old version with known CRITICAL CVEs; never imported by the app
ACTION="${1:-}"
ASSUME_YES="${2:-}"

pr_url() {
  local url path
  url="$(git remote get-url origin)"
  path="$(echo "$url" | sed -E 's#^(git@github.com:|https://github.com/)##; s#\.git$##')"
  echo "https://github.com/${path}/compare/main...${BRANCH}?expand=1"
}

require_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "ERROR: not a git repository." >&2; exit 1; }
  git remote get-url origin >/dev/null 2>&1 || { echo "ERROR: no 'origin' remote. Push the project to GitHub first." >&2; exit 1; }
}

case "$ACTION" in
  start)
    require_repo
    if [ -n "$(git status --porcelain)" ]; then
      echo "ERROR: you have uncommitted changes. Commit or stash them first." >&2; exit 1
    fi
    if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
      echo "ERROR: branch ${BRANCH} already exists. Run: $0 cleanup" >&2; exit 1
    fi
    START_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
    git checkout -q -b "$BRANCH"
    printf '%s\n' "$BAD_PACKAGE" >> requirements.txt
    git add requirements.txt
    git commit -q -m "demo: add vulnerable dependency to test the release gate"
    git push -u origin "$BRANCH"
    git checkout -q "$START_BRANCH"
    echo
    echo "Branch pushed. Now:"
    echo "  1. Open this link and create the pull request:"
    echo "     $(pr_url)"
    echo "  2. Watch the 'Trivy release gate' step FAIL, and 'Publish, sign, verify' be skipped."
    echo "  3. Take a screenshot, close the PR WITHOUT merging, then run: $0 cleanup"
    ;;
  cleanup)
    require_repo
    if [ "$ASSUME_YES" != "--yes" ]; then
      read -r -p "Delete local and remote branch ${BRANCH}? [y/N] " answer
      [[ "$answer" =~ ^[Yy]$ ]] || { echo "Cancelled."; exit 0; }
    fi
    CURRENT="$(git rev-parse --abbrev-ref HEAD)"
    [ "$CURRENT" != "$BRANCH" ] || git checkout -q main
    git branch -D "$BRANCH" 2>/dev/null || echo "(no local branch)"
    git push origin --delete "$BRANCH" 2>/dev/null || echo "(no remote branch)"
    echo "Cleaned up."
    ;;
  *)
    echo "Usage: $0 start | cleanup [--yes]" >&2
    exit 1
    ;;
esac
