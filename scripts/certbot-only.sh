#!/usr/bin/env bash
set -euo pipefail

# Certbot-only helper for www.meubusao.com
# Usage:
#   ./scripts/certbot-only.sh issue
#   ./scripts/certbot-only.sh renew
#   ./scripts/certbot-only.sh dry-run
#   ./scripts/certbot-only.sh           # auto: issue if missing, else renew

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo "Please run this script directly (do not source it)." >&2
  return 1 2>/dev/null || exit 1
fi

EMAIL="${EMAIL:-rlocoselli@yahoo.com.br}"
PRIMARY_DOMAIN="${PRIMARY_DOMAIN:-www.meubusao.com}"
SECONDARY_DOMAIN="${SECONDARY_DOMAIN:-meubusao.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_CERTS_DIR="${LOCAL_CERTS_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)/certs-local}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CHALLENGE_DIR="${CHALLENGE_DIR:-$PROJECT_ROOT/.well-known/acme-challenge}"
CERTBOT_BIN="${CERTBOT_BIN:-certbot}"
CERTBOT_USE_SUDO="${CERTBOT_USE_SUDO:-false}"
CERTBOT_CONFIG_DIR="${CERTBOT_CONFIG_DIR:-$LOCAL_CERTS_DIR/letsencrypt}"
CERTBOT_WORK_DIR="${CERTBOT_WORK_DIR:-$LOCAL_CERTS_DIR/work}"
CERTBOT_LOGS_DIR="${CERTBOT_LOGS_DIR:-$LOCAL_CERTS_DIR/logs}"
CERTBOT_LIVE_DIR="${CERTBOT_LIVE_DIR:-$CERTBOT_CONFIG_DIR/live}"

MODE="${1:-auto}"

check_certbot() {
  if command -v "$CERTBOT_BIN" >/dev/null 2>&1; then
    CERTBOT_BIN="$(command -v "$CERTBOT_BIN")"
    return 0
  fi

  if [[ -x "/snap/bin/certbot" ]]; then
    CERTBOT_BIN="/snap/bin/certbot"
    return 0
  fi

  echo "Error: certbot is not installed or not in PATH." >&2
  echo "Install it first, for example:" >&2
  echo "  sudo apt update && sudo apt install -y certbot" >&2
  echo "or" >&2
  echo "  sudo snap install --classic certbot" >&2
  exit 1
}

certbot_exec() {
  if [[ "$CERTBOT_USE_SUDO" == "true" ]]; then
    sudo "$CERTBOT_BIN" "$@"
  else
    "$CERTBOT_BIN" "$@"
  fi
}

prepare_certbot_dirs() {
  mkdir -p "$CERTBOT_CONFIG_DIR" "$CERTBOT_WORK_DIR" "$CERTBOT_LOGS_DIR" "$CHALLENGE_DIR"
}

issue_certificate() {
  prepare_certbot_dirs

  certbot_exec certonly \
    --manual \
    --preferred-challenges http \
    --manual-auth-hook "$SCRIPT_DIR/certbot-write-challenge.sh" \
    --manual-cleanup-hook "$SCRIPT_DIR/certbot-cleanup-challenge.sh" \
    --config-dir "$CERTBOT_CONFIG_DIR" \
    --work-dir "$CERTBOT_WORK_DIR" \
    --logs-dir "$CERTBOT_LOGS_DIR" \
    -d "$PRIMARY_DOMAIN" -d "$SECONDARY_DOMAIN" \
    --agree-tos \
    --email "$EMAIL" \
    --non-interactive
}

renew_certificate() {
  prepare_certbot_dirs

  certbot_exec renew \
    --config-dir "$CERTBOT_CONFIG_DIR" \
    --work-dir "$CERTBOT_WORK_DIR" \
    --logs-dir "$CERTBOT_LOGS_DIR"
}

dry_run_renewal() {
  prepare_certbot_dirs

  certbot_exec renew --dry-run \
    --config-dir "$CERTBOT_CONFIG_DIR" \
    --work-dir "$CERTBOT_WORK_DIR" \
    --logs-dir "$CERTBOT_LOGS_DIR"
}

check_certbot

resolve_mode() {
  if [[ "$MODE" != "auto" ]]; then
    return 0
  fi

  if [[ -f "$CERTBOT_LIVE_DIR/$PRIMARY_DOMAIN/fullchain.pem" && -f "$CERTBOT_LIVE_DIR/$PRIMARY_DOMAIN/privkey.pem" ]]; then
    MODE="renew"
  else
    MODE="issue"
  fi

  echo "Auto mode selected: $MODE"
}

save_local_copy() {
  local source_dir="$CERTBOT_LIVE_DIR/$PRIMARY_DOMAIN"
  local target_dir="$LOCAL_CERTS_DIR/$PRIMARY_DOMAIN/$(date +%F)"

  if [[ ! -f "$source_dir/fullchain.pem" || ! -f "$source_dir/privkey.pem" ]]; then
    echo "Warning: certificate files not found in $source_dir, skipping local backup."
    return 0
  fi

  mkdir -p "$target_dir"
  cp "$source_dir/fullchain.pem" "$target_dir/fullchain.pem"
  cp "$source_dir/privkey.pem" "$target_dir/privkey.pem"
  chmod 600 "$target_dir/privkey.pem"

  echo "Local backup saved to: $target_dir"
}

resolve_mode

case "$MODE" in
  issue)
    issue_certificate
    save_local_copy
    ;;
  renew)
    renew_certificate
    save_local_copy
    ;;
  dry-run)
    dry_run_renewal
    ;;
  *)
    echo "Usage: $0 {issue|renew|dry-run}" >&2
    exit 1
    ;;
esac
