#!/usr/bin/env python3
"""Собирает мировой декор Британии из набора decoratefacets.

Зачем: клиентская карта содержит только «жёсткие» статики. Вся обстановка,
которую на живом шарде держат динамическими предметами (бочки, полки, стулья,
книги, посуда, светильники, вывески), после конвертации карты отсутствует.
Пакет ModernDistro `decoratefacets` содержит готовые списки такой обстановки,
снятые с официальной карты (ThisIsMe / ServUO), и они совместимы с нашей
версией клиента (7.0.x, post-SA).

Что берём:
    decorations/britannia/decorations.cfg   — основной декор;
    decorations/britannia/signs.cfg         — вывески, таблички, части кораблей;
    decorations/britannia/lights.cfg        — светильники (свечи, фонари);
    decorations/britannia/newMagincia/*.cfg — Новая Маджинция (post-SA).

Что не берём:
    doors.cfg — двери уже расставлены `tools/merge_worlddoors.py`;
    blockers.cfg — невидимые блокираторы прохода, отдельное решение;
    oldMagincia/ — старая Маджинция, в клиенте 7.0.x её уже нет.

Дополнительно отбрасываем:
    * предметы дверных типов (их место занимает worlddoors.cfg);
    * предметы, у которых такой же график уже стоит статиком на этом тайле
      (z ± 1) — иначе декор двоился бы с картой;
    * позиции, которые уже есть в текущем сейве сервера (x,y,z,objtype);
    * дубли между файлами (например, корабли есть и в decorations, и в signs).

Использование:
    python3 tools/import_worlddecor.py
    python3 tools/import_worlddecor.py --check
    python3 tools/import_worlddecor.py --no-lights

Результат — `server/config/worlddecor.cfg` в формате decoratefacets, его
читает `server/scripts/include/worlddecor.inc`.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

FACET_DIR = ROOT / "server/pkg/tools/decoratefacets/decorations/britannia"

# Файлы фасета britannia: (путь, короткое имя источника).
SOURCES: list[tuple[str, str]] = [
    ("decorations.cfg", "decor"),
    ("signs.cfg", "signs"),
    ("lights.cfg", "lights"),
    ("newMagincia/decorations.cfg", "newmagincia"),
    ("newMagincia/signs.cfg", "newmagincia"),
]

DECOR_START_RE = re.compile(r"(?m)^Decor\s+(\d+)\s*\{")
ITEMDESC_BLOCK_RE = re.compile(
    r"(?m)^\s*(?:Item|Container|Door|Multi|Boat|Equipment|Weapon|Armor|Siege|Deed)"
    r"\s+(0x[0-9A-Fa-f]+|\d+)\s*[\r\n]*\{"
)
# Ключевые слова itemdesc, за которыми идёт objtype.
ITEMDESC_KW = "Item|Container|Door|Multi|Boat|Equipment|Weapon|Armor|Siege|Deed"


@dataclass(frozen=True)
class Decor:
    objtype: int
    x: int
    y: int
    z: int
    amount: int
    color: int
    realm: str
    name: str
    source: str
    key: int


def parse_decor_file(path: Path) -> list[dict[str, str]]:
    """Разбирает cfg decoratefacets на блоки Decor N { ... }."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[dict[str, str]] = []
    for match in DECOR_START_RE.finditer(text):
        end = text.find("\n}", match.end())
        if end < 0:
            continue
        fields: dict[str, str] = {"key": match.group(1)}
        block = text[match.end():end]
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            # Пустой Name (`Name` без значения) — нормальный случай.
            fields[parts[0].lower()] = parts[1].strip() if len(parts) > 1 else ""
        out.append(fields)
    return out


def to_decor(fields: dict[str, str], source: str) -> Decor | None:
    try:
        return Decor(
            objtype=int(fields["objtype"], 0),
            x=int(fields["x"]),
            y=int(fields["y"]),
            z=int(fields["z"]),
            amount=int(fields.get("amount") or 1),
            color=int(fields.get("color") or 0, 0),
            realm=(fields.get("realm") or "britannia").strip().lower(),
            name=(fields.get("name") or "").strip(),
            source=source,
            key=int(fields["key"]),
        )
    except (KeyError, ValueError):
        return None


def parse_door_types(path: Path) -> set[int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {int(x, 16) for x in re.findall(r"(?m)^Door\s+(0x[0-9A-Fa-f]+)", text)}


def parse_defined_objtypes(server_dir: Path) -> set[int]:
    """Objtype, объявленные в itemdesc.cfg (их POL умеет создавать).

    Объекты с номером >= 0x4000 (multis и прочие поздние типы) без descriptor
    POL создавать отказывается: `Objtype 0x... is not defined`.
    """
    defined: set[int] = set()
    for path in server_dir.rglob("itemdesc.cfg"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in ITEMDESC_BLOCK_RE.finditer(text):
            defined.add(int(match.group(1), 0))
    return defined


def parse_save_positions(path: Path) -> set[tuple[int, int, int, int]]:
    """Позиции уже существующих предметов из сейва (если он есть)."""
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    out: set[tuple[int, int, int, int]] = set()
    for match in re.finditer(r"(?m)^Item\s*\{", text):
        end = text.find("\n}", match.end())
        if end < 0:
            continue
        block = text[match.end():end]
        # Собственный декор уже стоит в мире; сравнивать нужно только с
        # предметами других подсистем (двери, сундуки торговцев и т.п.).
        if "WorldDecorStatic" in block:
            continue
        fields: dict[str, str] = {}
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) > 1:
                fields[parts[0].lower()] = parts[1].strip()
        try:
            out.add(
                (
                    int(fields["x"]),
                    int(fields["y"]),
                    int(fields["z"]),
                    int(fields["objtype"], 0),
                )
            )
        except (KeyError, ValueError):
            continue
    return out


class Statics:
    """Патченные статики POL: statidx.dat + statics.dat (график и z по тайлу)."""

    BLOCK = 8

    def __init__(self, realm_dir: Path, width: int = 7168, height: int = 4096) -> None:
        self.width = width
        self.height = height
        self.blocks_per_row = width // self.BLOCK
        self.index = (realm_dir / "statidx.dat").read_bytes()
        self.data = (realm_dir / "statics.dat").read_bytes()
        self._cache: dict[tuple[int, int], dict[tuple[int, int], list[tuple[int, int]]]] = {}

    def _block(self, bx: int, by: int) -> dict[tuple[int, int], list[tuple[int, int]]]:
        key = (bx, by)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        block_index = by * self.blocks_per_row + bx
        start = struct.unpack_from("<I", self.index, block_index * 4)[0]
        end = struct.unpack_from("<I", self.index, (block_index + 1) * 4)[0]
        result: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        for i in range(start, end):
            graphic, xy, z, _hue = struct.unpack_from("<HBbH", self.data, i * 6)
            result[(bx * self.BLOCK + (xy >> 4), by * self.BLOCK + (xy & 0xF))].append(
                (graphic, z)
            )
        self._cache[key] = result
        return result

    def at(self, x: int, y: int) -> list[tuple[int, int]]:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return []
        return self._block(x // self.BLOCK, y // self.BLOCK).get((x, y), [])

    def duplicates(self, decor: Decor, z_tolerance: int = 1) -> bool:
        return any(
            graphic == decor.objtype and abs(z - decor.z) <= z_tolerance
            for graphic, z in self.at(decor.x, decor.y)
        )


def collect(
    facet_dir: Path,
    door_types: set[int],
    statics: Statics,
    save_positions: set[tuple[int, int, int, int]],
    defined: set[int],
    with_lights: bool = True,
) -> tuple[list[Decor], dict[str, Counter]]:
    """Читает все источники и отбрасывает лишнее. Возвращает список и статистику."""
    stats: dict[str, Counter] = defaultdict(Counter)
    seen: dict[tuple[int, int, int, int], Decor] = {}
    result: list[Decor] = []

    for relative, source in SOURCES:
        if source == "lights" and not with_lights:
            continue
        path = facet_dir / relative
        if not path.exists():
            stats[source]["нет файла"] += 1
            continue
        blocks = parse_decor_file(path)
        stats[source]["всего"] += len(blocks)
        for fields in blocks:
            decor = to_decor(fields, source)
            if decor is None:
                stats[source]["битая запись"] += 1
                continue
            stats[source]["realm:" + decor.realm] += 1
            if decor.realm != "britannia":
                stats[source]["другой realm"] += 1
                continue
            if decor.objtype in door_types:
                stats[source]["дверной тип"] += 1
                continue
            if decor.objtype == 1:
                stats[source]["служебный объект"] += 1
                continue
            if decor.objtype >= 0x4000 and decor.objtype not in defined:
                # Корабельные пушки, ступени, маяки: art есть, descriptor
                # в ModernDistro отсутствует, POL такие objtype не создаёт.
                stats[source]["нет itemdesc"] += 1
                continue
            if not (0 <= decor.x < statics.width and 0 <= decor.y < statics.height):
                stats[source]["вне карты"] += 1
                continue
            position = (decor.x, decor.y, decor.z, decor.objtype)
            if position in save_positions:
                stats[source]["уже в сейве"] += 1
                continue
            if position in seen:
                stats[source]["дубль"] += 1
                continue
            if statics.duplicates(decor):
                stats[source]["дубль статика"] += 1
                continue
            seen[position] = decor
            result.append(decor)

    result.sort(key=lambda d: (d.x, d.y, d.z, d.objtype))
    return result, stats


def write_config(path: Path, items: list[Decor]) -> None:
    lines = [
        "// Мировой декор Британии (обстановка домов, лавок, таверн, доков).",
        "// Сгенерировано tools/import_worlddecor.py; не редактировать вручную.",
        "// Источник: ModernDistro decoratefacets (decorations/signs/lights).",
        "// Двери и невидимые блокираторы сюда не входят — см. worlddoors.cfg.",
        f"// Записей: {len(items)}.",
        "",
    ]
    for i, decor in enumerate(items):
        lines.extend(
            [
                f"Decor {i}",
                "{",
                f"\tName\t\t\t{decor.name}",
                f"\tObjtype\t\t\t0x{decor.objtype:04X}",
                f"\tAmount\t\t\t{decor.amount}",
                f"\tColor\t\t\t0x{decor.color:04X}",
                f"\tX\t\t\t{decor.x}",
                f"\tY\t\t\t{decor.y}",
                f"\tZ\t\t\t{decor.z}",
                "\tRealm\t\t\tbritannia",
                f"\tSource\t\t\t{decor.source}",
                "}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def check_config(path: Path, items: list[Decor]) -> int:
    if not path.exists():
        print(f"ОШИБКА: {path} не существует")
        return 1
    actual = [to_decor(f, "check") for f in parse_decor_file(path)]
    expected = sorted((d.x, d.y, d.z, d.objtype) for d in items)
    got = sorted((d.x, d.y, d.z, d.objtype) for d in actual if d)
    if expected != got:
        print(f"ОШИБКА: {path}: ожидалось {len(expected)}, записано {len(got)}")
        return 1
    print(f"OK: {path}: {len(got)} записей")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facet-dir", default=str(FACET_DIR), help="каталог фасета")
    parser.add_argument(
        "--doors-itemdesc",
        default=str(ROOT / "server/pkg/items/doors/config/itemdesc.cfg"),
        help="itemdesc дверей",
    )
    parser.add_argument(
        "--realm-dir",
        default=str(ROOT / "server/realm/britannia"),
        help="каталог realm с statidx.dat/statics.dat",
    )
    parser.add_argument(
        "--save",
        default=str(ROOT / "server/data/items.txt"),
        help="текущий сейв предметов (для проверки пересечений)",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "server/config/worlddecor.cfg"),
        help="куда записать конфиг",
    )
    parser.add_argument("--no-lights", action="store_true", help="без светильников")
    parser.add_argument("--check", action="store_true", help="только проверить output")
    args = parser.parse_args()

    facet_dir = Path(args.facet_dir)
    doors_itemdesc = Path(args.doors_itemdesc)
    realm_dir = Path(args.realm_dir)
    output = Path(args.output)

    for path in (doors_itemdesc, realm_dir / "statidx.dat", realm_dir / "statics.dat"):
        if not path.exists():
            print(f"ОШИБКА: не найден {path}")
            return 1

    door_types = parse_door_types(doors_itemdesc)
    statics = Statics(realm_dir)
    save_positions = parse_save_positions(Path(args.save))

    defined = parse_defined_objtypes(ROOT / "server")
    items, stats = collect(
        facet_dir,
        door_types,
        statics,
        save_positions,
        defined,
        with_lights=not args.no_lights,
    )

    for source in sorted(stats):
        counters = ", ".join(f"{name}: {count}" for name, count in sorted(stats[source].items()))
        print(f"{source}: {counters}")
    print(f"Итог: {len(items)} предметов декора")

    if args.check:
        return check_config(output, items)

    output.parent.mkdir(parents=True, exist_ok=True)
    write_config(output, items)
    print(f"Записано: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
