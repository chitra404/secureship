#!/usr/bin/env bash
# Verify that a published image was signed by THIS project's GitHub Actions workflow.
# Usage: ./scripts/verify-image.sh OWNER/REPOSITORY sha256:DIGEST [BRANCH]
# Example: ./scripts/verify-image.sh chitra/secureship sha256:abc...64hex...
set -euo pipefail

REPO_ARG="${1:-}"
DIGEST="${2:-}"
BRANCH="${3:-main}"

usage() { echo "Usage: $0 OWNER/REPOSITORY sha256:DIGEST [BRANCH]" >&2; exit 1; }

[ -n "$REPO_ARG" ] && [ -n "$DIGEST" ] || usage

if [[ ! "$REPO_ARG" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "ERROR: first argument must look like OWNER/REPOSITORY" >&2; exit 1
fi
if [[ ! "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  echo "ERROR: digest must look like sha256: followed by 64 hex characters" >&2; exit 1
fi
if ! command -v cosign >/dev/null 2>&1; then
  echo "ERROR: cosign is not installed. See https://docs.sigstore.dev/ for install steps." >&2
  exit 1
fi

IMAGE="ghcr.io/$(echo "$REPO_ARG" | tr '[:upper:]' '[:lower:]')@${DIGEST}"
IDENTITY="https://github.com/${REPO_ARG}/.github/workflows/secure-pipeline.yml@refs/heads/${BRANCH}"

echo "Image:    $IMAGE"
echo "Identity: $IDENTITY"
echo

cosign verify \
  --certificate-identity "$IDENTITY" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  "$IMAGE"

echo
echo "VERIFIED: this image was signed by the expected workflow."
