#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHALLENGE_DIR="${CHALLENGE_DIR:-$PROJECT_ROOT/.well-known/acme-challenge}"
CHALLENGE_FILE="${CHALLENGE_DIR}/${CERTBOT_TOKEN:-}"

if [[ -z "${CERTBOT_TOKEN:-}" ]]; then
  exit 0
fi

if [[ -f "$CHALLENGE_FILE" ]]; then
  rm -f "$CHALLENGE_FILE"
  echo "Challenge file removed: $CHALLENGE_FILE"
fi
