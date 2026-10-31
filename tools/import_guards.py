#!/usr/bin/env python3
"""Импортирует guard-посты World of Dream в конфиг мировых гвардов.

В WoD гварды — это NPC шаблонов `:guards:townguard` и `:guards:warrior`.
Берём их координаты, убираем дубликаты и создаём GuardNode (0x1887B),
который в ModernDistro сам спавнит `townguard`.

Использование:
    python3 tools/import_guards.py
    python3 tools/import_guards.py --check
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WOD_NPCS = ROOT / "src/WorldOfDream/data/npcs.txt"
OUTPUT = ROOT / "server/config/worldguards.cfg"
ALLOWED = {":guards:townguard", ":guards:warrior"}


@dataclass(frozen=True, order=True)
class GuardPost:
    x: int
    y: int
    z: int


def load_posts(path: Path) -> list[GuardPost]:
    text = path.read_text(encoding="utf-8", errors="replace")
    posts: set[GuardPost] = set()
    for template, body in re.findall(r"^NPC\s+(\S+)\s*\{(.*?)^\}", text, re.S | re.M):
        if template not in ALLOWED:
            continue
        x = re.search(r"^\s*X\s+(-?\d+)", body, re.M)
        y = re.search(r"^\s*Y\s+(-?\d+)", body, re.M)
        z = re.search(r"^\s*Z\s+(-?\d+)", body, re.M)
        if x and y and z:
            posts.add(GuardPost(int(x.group(1)), int(y.group(1)), int(z.group(1))))
    return sorted(posts)


def write_config(path: Path, posts: list[GuardPost]) -> None:
    lines = [
        "// Guard-посты Британии.",
        "// Сгенерировано tools/import_guards.py из World of Dream.",
        f"// Всего: {len(posts)}.",
        "",
    ]
    for i, post in enumerate(posts):
        lines += [
            f"Guard {i}",
            "{",
            f"\tX\t\t{post.x}",
            f"\tY\t\t{post.y}",
            f"\tZ\t\t{post.z}",
            "\tRealm\t\tbritannia",
            "}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wod", default=str(WOD_NPCS))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = Path(args.wod)
    if not source.exists():
        print(f"ОШИБКА: не найден {source}")
        return 1

    posts = load_posts(source)
    print(f"WoD: {len(posts)} уникальных guard-постов")

    output = Path(args.output)
    if args.check:
        if not output.exists():
            print(f"ОШИБКА: нет {output}")
            return 1
        text = output.read_text(encoding="utf-8", errors="replace")
        count = len(re.findall(r"^Guard\s+\d+", text, re.M))
        print(f"OK: {output}: {count} постов")
        return 0 if count == len(posts) else 1

    write_config(output, posts)
    print(f"Записано: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
