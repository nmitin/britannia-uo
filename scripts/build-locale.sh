#!/usr/bin/env bash
# Собирает клиентский Cliloc.rus из перевода сообщества и наших дополнений.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 tools/build_cliloc_ru.py \
  --base client/Cliloc.enu \
  --translation locale/ru/vendor/Cliloc.enu.community \
  --json locale/ru/cliloc_server_ru.json \
  --out client/Cliloc.rus
