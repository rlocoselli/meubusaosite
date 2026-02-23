#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHALLENGE_DIR="${CHALLENGE_DIR:-$PROJECT_ROOT/.well-known/acme-challenge}"
CHALLENGE_FILE="$CHALLENGE_DIR/$CERTBOT_TOKEN"
AUTO_GIT_PUSH="${AUTO_GIT_PUSH:-true}"
DEPLOY_WAIT_SECONDS="${DEPLOY_WAIT_SECONDS:-90}"
POLL_TIMEOUT_SECONDS="${POLL_TIMEOUT_SECONDS:-180}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-5}"
CHALLENGE_URL="https://${CERTBOT_DOMAIN}/.well-known/acme-challenge/${CERTBOT_TOKEN}"

mkdir -p "$CHALLENGE_DIR"
printf '%s' "$CERTBOT_VALIDATION" > "$CHALLENGE_FILE"

echo "Challenge file written: $CHALLENGE_FILE"
echo "Challenge URL expected: $CHALLENGE_URL"

if [[ "$AUTO_GIT_PUSH" == "true" ]]; then
	if command -v git >/dev/null 2>&1; then
		(
			cd "$PROJECT_ROOT"
			git add "$CHALLENGE_FILE"
			git commit -m "chore(acme): add challenge for ${CERTBOT_DOMAIN}" >/dev/null 2>&1 || true
			git push >/dev/null 2>&1 || true
		)
		echo "Git push attempted for challenge file."
	else
		echo "Warning: git not found, skipping auto commit/push."
	fi
fi

echo "Waiting ${DEPLOY_WAIT_SECONDS}s for Heroku deployment propagation..."
sleep "$DEPLOY_WAIT_SECONDS"

if command -v curl >/dev/null 2>&1; then
	elapsed=0
	while (( elapsed < POLL_TIMEOUT_SECONDS )); do
		if curl -fsS "$CHALLENGE_URL" >/dev/null 2>&1; then
			echo "Challenge URL is reachable: $CHALLENGE_URL"
			exit 0
		fi
		sleep "$POLL_INTERVAL_SECONDS"
		elapsed=$((elapsed + POLL_INTERVAL_SECONDS))
	done
	echo "Warning: challenge URL not reachable after ${POLL_TIMEOUT_SECONDS}s: $CHALLENGE_URL"
	echo "Certbot may fail unless deployment completes immediately."
else
	echo "Warning: curl not found, cannot verify challenge URL availability."
fi
