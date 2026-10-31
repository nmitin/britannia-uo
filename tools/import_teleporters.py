#!/usr/bin/env python3
"""Импортирует dungeon-телепорты World of Dream в конфиг мировых телепортов.

В WoD это предметы ObjType 0x6203 (graphic 0x1FD4) с CProp DestX/DestY/DestZ.
В нашем ModernDistro тот же предмет называется `dungtele` и имеет ObjType
0x16203, WalkOnScript makeDTele.

Скрипт:
- переводит 0x6203 -> 0x16203;
- убирает точные дубликаты;
- если на одном тайле лежит несколько телепортов (в WoD встречаются стопки
  до 9 штук), оставляет один — медианный по координатам назначения;
- проверяет, что источник и назначение в пределах нашей карты 7168x4096;
- пишет server/config/worldteleporters.cfg.

Использование:
    python3 tools/import_teleporters.py
    python3 tools/import_teleporters.py --check
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WOD_ITEMS = ROOT / "src/WorldOfDream/data/items.txt"
OUTPUT = ROOT / "server/config/worldteleporters.cfg"
WIDTH, HEIGHT = 7168, 4096


@dataclass(frozen=True, order=True)
class Teleporter:
    x: int
    y: int
    z: int
    dest_x: int
    dest_y: int
    dest_z: int


def parse_int(value: str) -> int:
    value = value.strip()
    if value.startswith(("i", "I")):
        value = value[1:]
    return int(value)


def load_teleporters(path: Path) -> list[Teleporter]:
    text = path.read_text(encoding="utf-8", errors="replace")
    result: list[Teleporter] = []
    for block in re.findall(r"Item\s*\{(.*?)\}", text, re.S):
        fields = dict(re.findall(r"^\s*(\w+)\s+(.+)$", block, re.M))
        if fields.get("ObjType", "").lower() not in ("0x6203", "0x16203"):
            continue
        cprops = dict(re.findall(r"^\s*CProp\s+(\w+)\s+(\S+)", block, re.M))
        if not all(k in cprops for k in ("DestX", "DestY", "DestZ")):
            continue
        result.append(
            Teleporter(
                int(fields["X"]),
                int(fields["Y"]),
                int(fields["Z"]),
                parse_int(cprops["DestX"]),
                parse_int(cprops["DestY"]),
                parse_int(cprops["DestZ"]),
            )
        )
    return result


def dedupe(items: list[Teleporter]) -> list[Teleporter]:
    # Точные дубликаты.
    unique = sorted(set(items))
    by_source: dict[tuple[int, int, int], list[Teleporter]] = defaultdict(list)
    for item in unique:
        by_source[(item.x, item.y, item.z)].append(item)

    chosen: list[Teleporter] = []
    dropped = 0
    for source, variants in by_source.items():
        variants.sort(key=lambda t: (t.dest_x, t.dest_y, t.dest_z))
        chosen.append(variants[len(variants) // 2])
        dropped += len(variants) - 1
    chosen.sort()
    return chosen, dropped


def valid(t: Teleporter) -> bool:
    return (
        0 <= t.x < WIDTH
        and 0 <= t.y < HEIGHT
        and 0 <= t.dest_x < WIDTH
        and 0 <= t.dest_y < HEIGHT
    )


def write_config(path: Path, items: list[Teleporter], dropped: int) -> None:
    lines = [
        "// Dungeon-телепорты Британии.",
        "// Сгенерировано tools/import_teleporters.py из World of Dream.",
        f"// Всего: {len(items)}; отброшено дублей/стопок: {dropped}.",
        "",
    ]
    for i, t in enumerate(items):
        lines += [
            f"Teleporter {i}",
            "{",
            f"\tX\t\t{t.x}",
            f"\tY\t\t{t.y}",
            f"\tZ\t\t{t.z}",
            f"\tDestX\t\t{t.dest_x}",
            f"\tDestY\t\t{t.dest_y}",
            f"\tDestZ\t\t{t.dest_z}",
            "\tRealm\t\tbritannia",
            "\tDestRealm\tbritannia",
            "}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wod", default=str(WOD_ITEMS))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = Path(args.wod)
    if not source.exists():
        print(f"ОШИБКА: не найден {source}")
        return 1

    raw = load_teleporters(source)
    items, dropped = dedupe(raw)
    items = [t for t in items if valid(t)]
    print(f"WoD: {len(raw)} телепортов, после дедупликации {len(items)} (отброшено {dropped})")

    output = Path(args.output)
    if args.check:
        if not output.exists():
            print(f"ОШИБКА: нет {output}")
            return 1
        text = output.read_text(encoding="utf-8", errors="replace")
        count = len(re.findall(r"^Teleporter\s+\d+", text, re.M))
        print(f"OK: {output}: {count} телепортов")
        return 0 if count == len(items) else 1

    write_config(output, items, dropped)
    print(f"Записано: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
