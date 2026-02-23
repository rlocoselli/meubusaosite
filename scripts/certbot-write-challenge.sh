#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHALLENGE_DIR="${CHALLENGE_DIR:-$PROJECT_ROOT/.well-known/acme-challenge}"
CHALLENGE_FILE="$CHALLENGE_DIR/$CERTBOT_TOKEN"
AUTO_GIT_PUSH="${AUTO_GIT_PUSH:-true}"
DEPLOY_WAIT_SECONDS="${DEPLOY_WAIT_SECONDS:-20}"
POLL_TIMEOUT_SECONDS="${POLL_TIMEOUT_SECONDS:-60}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-5}"
PUSH_TIMEOUT_SECONDS="${PUSH_TIMEOUT_SECONDS:-20}"
CHALLENGE_URL="https://${CERTBOT_DOMAIN}/.well-known/acme-challenge/${CERTBOT_TOKEN}"
STATE_FILE="$CHALLENGE_DIR/.pending-challenges"

mkdir -p "$CHALLENGE_DIR"
printf '%s' "$CERTBOT_VALIDATION" > "$CHALLENGE_FILE"

echo "Challenge file written: $CHALLENGE_FILE"
echo "Challenge URL expected: $CHALLENGE_URL"

printf '%s %s\n' "$CERTBOT_DOMAIN" "$CERTBOT_TOKEN" >> "$STATE_FILE"

if [[ "${CERTBOT_REMAINING_CHALLENGES:-0}" != "0" ]]; then
	echo "Waiting for remaining challenges to be prepared (${CERTBOT_REMAINING_CHALLENGES} left)."
	exit 0
fi

if [[ "$AUTO_GIT_PUSH" == "true" ]]; then
	if command -v git >/dev/null 2>&1; then
		(
			cd "$PROJECT_ROOT"
			git add "$CHALLENGE_DIR"
			if command -v timeout >/dev/null 2>&1; then
				timeout "$PUSH_TIMEOUT_SECONDS" git -c commit.gpgsign=false commit --no-gpg-sign -m "chore(acme): add challenge files for validation" || true
			else
				git -c commit.gpgsign=false commit --no-gpg-sign -m "chore(acme): add challenge files for validation" || true
			fi
			if command -v timeout >/dev/null 2>&1; then
				timeout "$PUSH_TIMEOUT_SECONDS" env GIT_TERMINAL_PROMPT=0 git push || true
			else
				env GIT_TERMINAL_PROMPT=0 git push || true
			fi
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
		all_ok=true
		while read -r domain token; do
			[[ -z "$domain" || -z "$token" ]] && continue
			url="https://${domain}/.well-known/acme-challenge/${token}"
			if ! curl -fsS "$url" >/dev/null 2>&1; then
				all_ok=false
				break
			fi
		done < "$STATE_FILE"

		if [[ "$all_ok" == "true" ]]; then
			echo "All challenge URLs are reachable."
			exit 0
		fi
		sleep "$POLL_INTERVAL_SECONDS"
		elapsed=$((elapsed + POLL_INTERVAL_SECONDS))
	done
	echo "Warning: challenge URLs not all reachable after ${POLL_TIMEOUT_SECONDS}s"
	echo "Certbot may fail unless deployment completes immediately."
else
	echo "Warning: curl not found, cannot verify challenge URL availability."
fi
