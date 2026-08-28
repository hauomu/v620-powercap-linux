#!/usr/bin/env bash
set -euo pipefail
# SPDX-License-Identifier: GPL-2.0-only
BIN_DIR="${BIN_DIR:-/usr/local/sbin}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
CONFIG_FILE="${CONFIG_FILE:-/etc/v620-powercap.conf}"
[[ "${EUID:-$(id -u)}" -eq 0 ]] || { echo "ERROR: run uninstall.sh with sudo" >&2; exit 1; }
systemctl disable --now v620-powercap.service 2>/dev/null || true
rm -f "$SYSTEMD_DIR/v620-powercap.service" "$BIN_DIR/v620-powercap"
[[ "${KEEP_CONFIG:-0}" == "1" ]] || rm -f "$CONFIG_FILE"
systemctl daemon-reload
echo "V620 power-cap runtime/service removed."
