#!/usr/bin/env python3
"""Собирает единый список мировых дверей из сейва World of Dream и текущего
конфига decoratefacets, проверяя каждую дверь по статикам сервера.

Зачем: в клиентской карте двери не являются статиками. World of Dream — это
старый рабочий сервер, в сейве которого (`data/items.txt`) есть готовые двери.
Текущий набор из decoratefacets покрывает более новую карту. Объединяем оба
источника, оставляя только двери, рядом с которыми в патченных статиках есть
стена/проём (в пределах одного тайла и z ± 2).

Использование:
    python3 tools/merge_worlddoors.py
    python3 tools/merge_worlddoors.py --output server/config/worlddoors.cfg
    python3 tools/merge_worlddoors.py --check

Результат — конфиг в формате decoratefacets, который читает
`server/scripts/include/worlddoors.inc`.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Door:
    x: int
    y: int
    z: int
    objtype: int
    source: str  # "wod" | "decor"


ITEM_BLOCK_RE = re.compile(r"Item\s*\{(.*?)\}", re.S)
DECOR_BLOCK_RE = re.compile(r"Decor\s+\d+\s*\{(.*?)\}", re.S)
FIELD_RE = re.compile(r"^\s*(\w+)\s+(.+?)\s*$", re.M)


def parse_fields(block: str) -> dict[str, str]:
    return {k.lower(): v for k, v in FIELD_RE.findall(block)}


def parse_wod_doors(path: Path, door_types: set[int]) -> list[Door]:
    text = path.read_text(encoding="utf-8", errors="replace")
    doors: list[Door] = []
    for block in ITEM_BLOCK_RE.findall(text):
        fields = parse_fields(block)
        try:
            objtype = int(fields["objtype"], 0)
            if objtype not in door_types:
                continue
            realm = fields.get("realm", "britannia").strip().lower()
            if realm != "britannia":
                continue
            doors.append(
                Door(int(fields["x"]), int(fields["y"]), int(fields["z"]), objtype, "wod")
            )
        except (KeyError, ValueError):
            continue
    return doors


def parse_decor_doors(path: Path) -> list[Door]:
    text = path.read_text(encoding="utf-8", errors="replace")
    doors: list[Door] = []
    for block in DECOR_BLOCK_RE.findall(text):
        fields = parse_fields(block)
        try:
            doors.append(
                Door(
                    int(fields["x"]),
                    int(fields["y"]),
                    int(fields["z"]),
                    int(fields["objtype"], 0),
                    "decor",
                )
            )
        except (KeyError, ValueError):
            continue
    return doors


def parse_door_types(path: Path) -> set[int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {int(x, 16) for x in re.findall(r"^Door\s+(0x[0-9A-Fa-f]+)", text, re.M)}


class Statics:
    """Патченные статики POL: statidx.dat + statics.dat."""

    BLOCK = 8

    def __init__(self, realm_dir: Path, width: int = 7168) -> None:
        self.width = width
        self.blocks_per_row = width // self.BLOCK
        self.index = (realm_dir / "statidx.dat").read_bytes()
        self.data = (realm_dir / "statics.dat").read_bytes()
        self._cache: dict[tuple[int, int], dict[tuple[int, int], list[int]]] = {}

    def _block(self, bx: int, by: int) -> dict[tuple[int, int], list[int]]:
        key = (bx, by)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        bi = by * self.blocks_per_row + bx
        start = struct.unpack_from("<I", self.index, bi * 4)[0]
        end = struct.unpack_from("<I", self.index, (bi + 1) * 4)[0]
        result: dict[tuple[int, int], list[int]] = defaultdict(list)
        for i in range(start, end):
            graphic, xy, z, _hue = struct.unpack_from("<HBbH", self.data, i * 6)
            result[(bx * 8 + (xy >> 4), by * 8 + (xy & 0xF))].append(z)
        self._cache[key] = result
        return result

    def z_at(self, x: int, y: int) -> list[int]:
        if x < 0 or y < 0 or x >= self.width or y >= 4096:
            return []
        return self._block(x // 8, y // 8).get((x, y), [])

    def near_door(self, door: Door, radius: int = 1, z_tolerance: int = 2) -> bool:
        for yy in range(door.y - radius, door.y + radius + 1):
            for xx in range(door.x - radius, door.x + radius + 1):
                for z in self.z_at(xx, yy):
                    if abs(z - door.z) <= z_tolerance:
                        return True
        return False


def merge_doors(wod: list[Door], decor: list[Door]) -> list[Door]:
    """Объединяет двери по (x,y); WoD имеет приоритет, z-уровни кластеризуются."""
    grouped: dict[tuple[int, int], list[Door]] = defaultdict(list)
    for door in wod:
        grouped[(door.x, door.y)].append(door)
    for door in decor:
        grouped[(door.x, door.y)].append(door)

    merged: list[Door] = []
    for (x, y), candidates in grouped.items():
        # Сначала WoD, затем decoratefacets; внутри источника — по z.
        candidates.sort(key=lambda d: (0 if d.source == "wod" else 1, d.z))
        levels: list[int] = []
        for door in candidates:
            if any(abs(door.z - z) <= 2 for z in levels):
                continue
            levels.append(door.z)
            merged.append(door)

    merged.sort(key=lambda d: (d.x, d.y, d.z, d.objtype))
    return merged


def write_config(path: Path, doors: list[Door], wod_total: int, decor_total: int) -> None:
    lines = [
        "// Мировые двери Британии.",
        "// Сгенерировано tools/merge_worlddoors.py; не редактировать вручную.",
        f"// Источники: World of Dream items.txt ({wod_total} дверей),",
        f"//            decoratefacets britannia/doors.cfg ({decor_total} дверей).",
        "// Оставлены только двери, проверенные по патченным статикам карты.",
        "",
    ]
    for i, door in enumerate(doors):
        lines.extend(
            [
                f"Decor {i}",
                "{",
                f"\tName\t\t\tworld door ({door.source})",
                f"\tObjtype\t\t\t0x{door.objtype:04X}",
                "\tAmount\t\t\t1",
                "\tColor\t\t\t0x0",
                f"\tX\t\t\t{door.x}",
                f"\tY\t\t\t{door.y}",
                f"\tZ\t\t\t{door.z}",
                "\tRealm\t\t\tbritannia",
                "}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def check_config(path: Path, doors: list[Door]) -> int:
    """Проверяет, что записанный конфиг совпадает с ожидаемым списком."""
    if not path.exists():
        print(f"ОШИБКА: {path} не существует")
        return 1
    actual = parse_decor_doors(path)
    expected = sorted((d.x, d.y, d.z, d.objtype) for d in doors)
    got = sorted((d.x, d.y, d.z, d.objtype) for d in actual)
    if expected != got:
        print(f"ОШИБКА: {path}: ожидалось {len(expected)}, записано {len(got)}")
        return 1
    print(f"OK: {path}: {len(got)} дверей")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wod", default=str(ROOT / "src/WorldOfDream/data/items.txt"), help="items.txt WoD"
    )
    parser.add_argument(
        "--decor",
        default=str(
            ROOT / "server/pkg/tools/decoratefacets/decorations/britannia/doors.cfg"
        ),
        help="doors.cfg decoratefacets",
    )
    parser.add_argument(
        "--itemdesc",
        default=str(ROOT / "server/pkg/items/doors/config/itemdesc.cfg"),
        help="itemdesc дверей",
    )
    parser.add_argument(
        "--realm-dir",
        default=str(ROOT / "server/realm/britannia"),
        help="каталог realm с statidx.dat/statics.dat",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "server/config/worlddoors.cfg"),
        help="куда записать объединённый конфиг",
    )
    parser.add_argument("--check", action="store_true", help="только проверить output")
    parser.add_argument("--all", action="store_true", help="не отбрасывать невалидные двери")
    args = parser.parse_args()

    wod_path = Path(args.wod)
    decor_path = Path(args.decor)
    itemdesc_path = Path(args.itemdesc)
    realm_dir = Path(args.realm_dir)
    output = Path(args.output)

    for path in (wod_path, decor_path, itemdesc_path):
        if not path.exists():
            print(f"ОШИБКА: не найден {path}")
            return 1

    door_types = parse_door_types(itemdesc_path)
    wod = parse_wod_doors(wod_path, door_types)
    decor = parse_decor_doors(decor_path)
    statics = Statics(realm_dir)

    if args.all:
        wod_valid, decor_valid = wod, decor
    else:
        wod_valid = [d for d in wod if statics.near_door(d)]
        decor_valid = [d for d in decor if statics.near_door(d)]

    merged = merge_doors(wod_valid, decor_valid)
    from_wod = sum(1 for d in merged if d.source == "wod")
    from_decor = len(merged) - from_wod

    print(f"World of Dream: {len(wod)} дверей, прошло проверку {len(wod_valid)}")
    print(f"decoratefacets: {len(decor)} дверей, прошло проверку {len(decor_valid)}")
    print(f"Итог: {len(merged)} (WoD {from_wod}, decoratefacets {from_decor})")

    if args.check:
        return check_config(output, merged)

    output.parent.mkdir(parents=True, exist_ok=True)
    write_config(output, merged, len(wod), len(decor))
    print(f"Записано: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
