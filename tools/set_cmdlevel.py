#!/usr/bin/env python3
"""Выставляет CmdLevel персонажу в server/data/pcs.txt.

Нужно, когда персонаж был создан как player, а аккаунту позже выдали admin:
POL хранит cmdlevel в pcs.txt и при загрузке по умолчанию ставит player.
Скрипт отказывается работать, если сервер слушает 2593 — иначе сейв
перезапишется при остановке сервера.

Использование:
    python3 tools/set_cmdlevel.py --name TestAdmin2 --level admin
"""
from __future__ import annotations

import argparse
import shutil
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCS = ROOT / "server/data/pcs.txt"


def server_running(port: int = 2593) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="имя персонажа")
    parser.add_argument("--level", default="admin", help="player/coun/seer/gm/admin")
    parser.add_argument("--file", default=str(PCS), help="путь к pcs.txt")
    parser.add_argument("--force", action="store_true", help="не проверять порт 2593")
    args = parser.parse_args()

    if not args.force and server_running():
        print("ОШИБКА: сервер слушает 2593. Останови его и повтори.")
        return 1

    path = Path(args.file)
    if not path.exists():
        print(f"ОШИБКА: не найден {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "Character" and i + 1 < len(lines) and lines[i + 1].strip() == "{":
            block_end = None
            for j in range(i + 2, len(lines)):
                if lines[j].strip() == "}":
                    block_end = j
                    break
            if block_end is None:
                continue
            block = "".join(lines[i:block_end])
            if any(
                ln.strip().split("\t")[0].split()[0] == "Name"
                and ln.strip().split(None, 1)[1].strip() == args.name
                for ln in lines[i:block_end]
                if ln.strip().startswith("Name")
            ):
                start = i
                end = block_end
                break

    if start is None:
        print(f"ОШИБКА: персонаж '{args.name}' не найден в {path}")
        return 1

    new_lines = []
    replaced = False
    for idx, line in enumerate(lines):
        if start < idx < end and line.strip().startswith("CmdLevel"):
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}CmdLevel\t{args.level}\n")
            replaced = True
        else:
            new_lines.append(line)
        if idx == start + 2 and not replaced:
            # Вставляем после Name/Serial, если CmdLevel ещё нет.
            # (Проверка replaced ниже всё равно заменит существующий.)
            pass

    if not replaced:
        # Вставляем CmdLevel после строки Name внутри блока.
        for idx in range(start + 1, end):
            if lines[idx].strip().startswith("Name"):
                new_lines.insert(idx + 1, f"\tCmdLevel\t{args.level}\n")
                break

    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    path.write_text("".join(new_lines), encoding="utf-8")
    print(f"OK: {args.name}: CmdLevel {args.level}. Бэкап: {backup}")
    print("Теперь запусти сервер заново.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
