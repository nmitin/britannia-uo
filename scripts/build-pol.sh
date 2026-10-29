#!/usr/bin/env bash
# Сборка ядра POL 100.2.0 и копирование бинарников в server/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/src/polserver"
PATCH="$ROOT/patches/pol-100.2.0-linux-build.patch"

if [ ! -d "$SRC" ]; then
  echo "Нет исходников: $SRC" >&2
  echo "Клонируйте: git clone --branch v100.2.0 https://github.com/polserver/polserver.git $SRC" >&2
  exit 1
fi

cd "$SRC"

# Патчи нужны для сборки на современных дистрибутивах:
#   * boost stacktrace header-only (иначе ищется libbacktrace)
#   * curl без libssh2 (иначе статическая libcurl требует libssh2)
if [ -f "$PATCH" ] && git apply --check "$PATCH" 2>/dev/null; then
  git apply "$PATCH"
  echo "Патч сборки применён."
fi

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DUSE_BOOST_HEADER_STACKTRACE=ON "${@}"
cmake --build build -j"$(nproc)"

install -m 755 bin/pol bin/ecompile bin/uoconvert bin/uotool bin/poltool bin/runecl "$ROOT/server/"
echo "Готово: бинарники в $ROOT/server/"
