#!/usr/bin/env bash
# Компиляция всех скриптов дистрибутива (ecompile -A).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/server"

./ecompile -A -b -f "$@"
