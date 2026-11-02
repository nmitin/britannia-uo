#!/usr/bin/env python3
"""Импортирует guard-посты World of Dream в конфиг мировых гвардов.

В WoD гварды — это NPC шаблонов `:guards:townguard`, `:guards:warrior`,
`:guards:orderguard` и `:guards:chaosguard`. Берём их координаты, убираем
дубликаты и создаём GuardNode (0x1887B), который в ModernDistro сам спавнит
NPC указанного типа (CProp `Type`).

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

# Шаблон NPC в WoD -> тип узла GuardNode в нашем мире.
ALLOWED = {
    ":guards:townguard": "townguard",
    ":guards:warrior": "townguard",
    ":guards:orderguard": "orderguard",
    ":guards:chaosguard": "chaosguard",
}

# Порядок типов в конфиге: сначала обычные посты, потом фракционные.
TYPE_ORDER = {"townguard": 0, "orderguard": 1, "chaosguard": 2}


@dataclass(frozen=True, order=True)
class GuardPost:
    x: int
    y: int
    z: int
    node_type: str = "townguard"


def load_posts(path: Path) -> list[GuardPost]:
    text = path.read_text(encoding="utf-8", errors="replace")
    posts: dict[tuple[int, int, int], GuardPost] = {}
    for template, body in re.findall(r"^NPC\s+(\S+)\s*\{(.*?)^\}", text, re.S | re.M):
        node_type = ALLOWED.get(template)
        if not node_type:
            continue
        x = re.search(r"^\s*X\s+(-?\d+)", body, re.M)
        y = re.search(r"^\s*Y\s+(-?\d+)", body, re.M)
        z = re.search(r"^\s*Z\s+(-?\d+)", body, re.M)
        if not (x and y and z):
            continue
        post = GuardPost(int(x.group(1)), int(y.group(1)), int(z.group(1)), node_type)
        posts.setdefault((post.x, post.y, post.z), post)
    return sorted(posts.values(), key=lambda p: (TYPE_ORDER[p.node_type], p.x, p.y, p.z))


def write_config(path: Path, posts: list[GuardPost]) -> None:
    counts: dict[str, int] = {}
    for post in posts:
        counts[post.node_type] = counts.get(post.node_type, 0) + 1
    summary = ", ".join(f"{kind}: {count}" for kind, count in sorted(counts.items()))

    lines = [
        "// Guard-посты Британии.",
        "// Сгенерировано tools/import_guards.py из World of Dream.",
        f"// Всего: {len(posts)} ({summary}).",
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
            f"\tType\t\t{post.node_type}",
            "}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_config(path: Path) -> list[GuardPost]:
    text = path.read_text(encoding="utf-8", errors="replace")
    posts: list[GuardPost] = []
    for body in re.findall(r"^Guard\s+\d+\s*\{(.*?)^\}", text, re.S | re.M):
        x = re.search(r"^\s*X\s+(-?\d+)", body, re.M)
        y = re.search(r"^\s*Y\s+(-?\d+)", body, re.M)
        z = re.search(r"^\s*Z\s+(-?\d+)", body, re.M)
        kind = re.search(r"^\s*Type\s+(\S+)", body, re.M)
        if not (x and y and z):
            continue
        posts.append(
            GuardPost(
                int(x.group(1)),
                int(y.group(1)),
                int(z.group(1)),
                kind.group(1) if kind else "townguard",
            )
        )
    return posts


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
        actual = parse_config(output)
        expected = sorted((p.x, p.y, p.z, p.node_type) for p in posts)
        got = sorted((p.x, p.y, p.z, p.node_type) for p in actual)
        if expected != got:
            print(f"ОШИБКА: {output}: ожидалось {len(expected)}, записано {len(got)}")
            return 1
        print(f"OK: {output}: {len(got)} постов")
        return 0

    write_config(output, posts)
    print(f"Записано: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
