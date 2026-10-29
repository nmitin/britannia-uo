#!/usr/bin/env bash
# Устанавливает пользовательский systemd-сервис для шарда.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT="$UNIT_DIR/uo-shard.service"

mkdir -p "$UNIT_DIR" "$ROOT/logs"
cat > "$UNIT" <<UNITEOF
[Unit]
Description=Ultima Online shard (POL)
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT/server
ExecStart=$ROOT/server/pol
Restart=on-failure
RestartSec=5
StandardOutput=append:$ROOT/logs/pol-stdout.log
StandardError=append:$ROOT/logs/pol-stderr.log

[Install]
WantedBy=default.target
UNITEOF

systemctl --user daemon-reload
systemctl --user enable --now uo-shard.service
echo "Сервис uo-shard запущен. Статус: systemctl --user status uo-shard"
