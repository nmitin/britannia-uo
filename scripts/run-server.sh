#!/usr/bin/env bash
# Запуск сервера POL. Логи — в logs/pol.log.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/server"

mkdir -p "$ROOT/logs"
exec ./pol "$@"
