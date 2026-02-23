#!/usr/bin/env bash
set -euo pipefail

# Certbot-only helper for www.meubusao.com
# Usage:
#   ./scripts/certbot-only.sh issue
#   ./scripts/certbot-only.sh renew
#   ./scripts/certbot-only.sh dry-run

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

MODE="${1:-renew}"

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

issue_certificate() {
  mkdir -p "$CHALLENGE_DIR"

  sudo "$CERTBOT_BIN" certonly \
    --manual \
    --preferred-challenges http \
    --manual-public-ip-logging-ok \
    --manual-auth-hook "$SCRIPT_DIR/certbot-write-challenge.sh" \
    --manual-cleanup-hook "$SCRIPT_DIR/certbot-cleanup-challenge.sh" \
    -d "$PRIMARY_DOMAIN" -d "$SECONDARY_DOMAIN" \
    --agree-tos \
    --email "$EMAIL" \
    --non-interactive
}

renew_certificate() {
  sudo "$CERTBOT_BIN" renew
}

dry_run_renewal() {
  sudo "$CERTBOT_BIN" renew --dry-run
}

check_certbot

save_local_copy() {
  local source_dir="/etc/letsencrypt/live/$PRIMARY_DOMAIN"
  local target_dir="$LOCAL_CERTS_DIR/$PRIMARY_DOMAIN/$(date +%F)"

  if [[ ! -f "$source_dir/fullchain.pem" || ! -f "$source_dir/privkey.pem" ]]; then
    echo "Warning: certificate files not found in $source_dir, skipping local backup."
    return 0
  fi

  mkdir -p "$target_dir"
  sudo cp "$source_dir/fullchain.pem" "$target_dir/fullchain.pem"
  sudo cp "$source_dir/privkey.pem" "$target_dir/privkey.pem"
  sudo chown "$USER":"$USER" "$target_dir/fullchain.pem" "$target_dir/privkey.pem"
  chmod 600 "$target_dir/privkey.pem"

  echo "Local backup saved to: $target_dir"
}

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
