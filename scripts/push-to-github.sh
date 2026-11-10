#!/usr/bin/env bash
# Push this project to a NEW, EMPTY GitHub repository (first-time setup).
# Usage: ./scripts/push-to-github.sh GITHUB_USERNAME [REPO_NAME]
# Create the empty repository on github.com first. REPO_NAME defaults to "secureship".
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

USERNAME="${1:-}"
REPO="${2:-secureship}"

if [ -z "$USERNAME" ]; then
  echo "Usage: $0 GITHUB_USERNAME [REPO_NAME]" >&2
  exit 1
fi

if [[ ! "$REPO" =~ ^[a-z0-9._-]+$ ]]; then
  echo "ERROR: repository name must be lowercase (letters, digits, . _ -). GHCR needs this." >&2
  exit 1
fi

# REMOTE_URL can be set for testing; normally the GitHub HTTPS URL is used.
REMOTE_URL="${REMOTE_URL:-https://github.com/${USERNAME}/${REPO}.git}"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is not installed." >&2
  exit 1
fi

if [ -z "$(git config user.email || true)" ] || [ -z "$(git config user.name || true)" ]; then
  echo "ERROR: Git does not know who you are. Run these once, then try again:" >&2
  echo "  git config --global user.name  \"Your Name\"" >&2
  echo "  git config --global user.email \"you@example.com\"" >&2
  exit 1
fi

if [ ! -d .git ]; then
  echo "==> Initialising git repository"
  git init -q
fi

git checkout -q -B main

if git remote get-url origin >/dev/null 2>&1; then
  EXISTING="$(git remote get-url origin)"
  if [ "$EXISTING" != "$REMOTE_URL" ]; then
    echo "ERROR: 'origin' already points to $EXISTING" >&2
    echo "Expected $REMOTE_URL. Fix it with: git remote set-url origin $REMOTE_URL" >&2
    exit 1
  fi
else
  git remote add origin "$REMOTE_URL"
fi

git add .
if git diff --cached --quiet; then
  echo "==> Nothing new to commit"
else
  git commit -q -m "Initial SecureShip implementation"
  echo "==> Committed"
fi

echo "==> Pushing to $REMOTE_URL (GitHub may ask for your login)"
git push -u origin main

echo
echo "Done. Open https://github.com/${USERNAME}/${REPO}/actions to watch the pipeline."
