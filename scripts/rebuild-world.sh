#!/usr/bin/env bash
# Пересборка мира из файлов клиента. По умолчанию — Британия (Felucca, ML).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/server"

echo "[1/4] Конфиги мульти и тайлов"
./uoconvert multis outdir=config
./uoconvert tiles outdir=config
./uoconvert landtiles outdir=config

echo "[2/4] Карта"
./uoconvert map realm=britannia mapid=0 usedif=1 width=7168 height=4096

echo "[3/4] Статики"
./uoconvert statics realm=britannia

echo "[4/4] Maptile"
./uoconvert maptile realm=britannia

echo "Мир пересобран: $ROOT/server/realm/britannia"
