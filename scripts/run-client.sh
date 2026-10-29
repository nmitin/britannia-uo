#!/usr/bin/env bash
# Запуск клиента ClassicUO.
# По умолчанию подключается к 127.0.0.1:2593. Аргументы можно передать дальше:
#   ./scripts/run-client.sh -ip 192.168.1.10 -port 2593
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/clientapp"

exec ./ClassicUO \
  -uopath "$ROOT/client" \
  -ip "${UO_HOST:-127.0.0.1}" \
  -port "${UO_PORT:-2593}" \
  "$@"
