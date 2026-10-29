#!/usr/bin/env bash
# Архив состояния шарда. Хранит последние 14 копий.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/backups"
mkdir -p "$DEST"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$DEST/uo-$STAMP.tar.gz"

tar -czf "$ARCHIVE" -C "$ROOT" \
  server/data server/config server/regions server/pol.cfg \
  locale client/Cliloc.rus 2>/dev/null || true

ls -1t "$DEST"/uo-*.tar.gz | tail -n +15 | xargs -r rm -f
echo "Резервная копия: $ARCHIVE"
