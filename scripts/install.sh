#!/usr/bin/env bash
set -euo pipefail
# SPDX-License-Identifier: GPL-2.0-only

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BIN_DIR="${BIN_DIR:-/usr/local/sbin}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
CONFIG_FILE="${CONFIG_FILE:-/etc/v620-powercap.conf}"
WATTS=""
PCI=""

usage() {
cat <<'EOF'
Usage:
  sudo ./scripts/install.sh --watts WATTS [--pci BDF]

Optional environment overrides:
  BIN_DIR=/usr/local/sbin
  SYSTEMD_DIR=/etc/systemd/system
  CONFIG_FILE=/etc/v620-powercap.conf
EOF
}

while (($#)); do
    case "$1" in
        --watts) WATTS="${2:-}"; shift 2 ;;
        --pci) PCI="${2:-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown argument: $1" >&2; usage; exit 2 ;;
    esac
done

[[ "${EUID:-$(id -u)}" -eq 0 ]] || { echo "ERROR: run install.sh with sudo" >&2; exit 1; }
[[ "$WATTS" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "ERROR: --watts is required and must be numeric" >&2; exit 2; }

install -d -m 0755 "$BIN_DIR" "$SYSTEMD_DIR"
install -m 0755 "$SCRIPT_DIR/v620-powercap" "$BIN_DIR/v620-powercap"

{
    printf 'POWER_CAP_W=%q\n' "$WATTS"
    if [[ -n "$PCI" ]]; then
        printf 'V620_PCI=%q\n' "$PCI"
    else
        printf '# V620_PCI=0000:53:00.0\n'
    fi
} > "$CONFIG_FILE"
chmod 0644 "$CONFIG_FILE"

BIN_PATH="$BIN_DIR/v620-powercap"
UNIT="$SYSTEMD_DIR/v620-powercap.service"
sed -e "s|@BIN_PATH@|$BIN_PATH|g" -e "s|@CONFIG_PATH@|$CONFIG_FILE|g" \
    "$REPO_ROOT/systemd/v620-powercap.service.in" > "$UNIT"

systemctl daemon-reload
systemctl enable --now v620-powercap.service

echo "Installed tool:    $BIN_PATH"
echo "Installed config:  $CONFIG_FILE"
echo "Installed service: $UNIT"
systemctl --no-pager --full status v620-powercap.service || true
