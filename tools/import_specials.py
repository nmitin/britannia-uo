#!/usr/bin/env python3
"""Импортирует особых NPC World of Dream (лекари, стейблмастеры) в конфиг.

В WoD это NPC шаблонов `:healer:healer` и `:merchants:stablemaster`.
Берём их координаты/имена, отбрасываем точки рядом со штатными
merchant-узлами ModernDistro (nodes.xml, фасет Felucca/britannia) и пишем
config/worldspecials.cfg. На сервере по этим записям создаются MerchantNode,
которые сами спавнят и воскрешают NPC.

Использование:
    python3 tools/import_specials.py
    python3 tools/import_specials.py --check
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WOD_NPCS = ROOT / "src/WorldOfDream/data/npcs.txt"
STOCK_NODES = ROOT / "server/pkg/systems/merchantnodes/backups/nodes.xml"
OUTPUT = ROOT / "server/config/worldspecials.cfg"

# Шаблон WoD -> шаблон ModernDistro (npcdesc.cfg).
ALLOWED = {":healer:healer": "healer", ":merchants:stablemaster": "stablemaster"}

# Точка WoD отбрасывается, если в этом радиусе от неё уже есть штатный узел
# того же шаблона.
DEDUP_RANGE = 25


@dataclass(frozen=True)
class SpecialNpc:
    template: str
    x: int
    y: int
    z: int
    name: str
    gender: int


def parse_wod(path: Path) -> list[SpecialNpc]:
    text = path.read_text(encoding="utf-8", errors="replace")
    npcs: list[SpecialNpc] = []
    for template, body in re.findall(r"^NPC\s+(\S+)\s*\{(.*?)^\}", text, re.S | re.M):
        if template not in ALLOWED:
            continue
        x = re.search(r"^\s*X\s+(-?\d+)", body, re.M)
        y = re.search(r"^\s*Y\s+(-?\d+)", body, re.M)
        z = re.search(r"^\s*Z\s+(-?\d+)", body, re.M)
        name = re.search(r'^\s*Name\s+(.+)$', body, re.M)
        gender = re.search(r"^\s*Gender\s+(\d+)", body, re.M)
        if not (x and y and z and name):
            continue
        npcs.append(SpecialNpc(
            template=ALLOWED[template],
            x=int(x.group(1)),
            y=int(y.group(1)),
            z=int(z.group(1)),
            name=name.group(1).split()[0],
            gender=int(gender.group(1)) if gender else 0,
        ))
    return npcs


def read_packed_string(cprops: str, key: str) -> str | None:
    """Читает значение строкового ключа из packed-строки POL (S4:NameS7:value)."""
    m = re.search(r"S\d+:" + key + r"S(\d+):", cprops)
    if not m:
        return None
    start = m.end()
    return cprops[start:start + int(m.group(1))]


def parse_stock_nodes(path: Path) -> dict[str, list[tuple[int, int]]]:
    """Штатные merchant-узлы фасета Felucca: шаблон -> координаты."""
    root = ET.parse(path).getroot()
    stock: dict[str, list[tuple[int, int]]] = {}
    facet = root.find("Felucca")
    if facet is None or facet.get("Realm") != "britannia":
        return stock
    for section in facet.findall("MerchantNodes"):
        for node in section.findall("Node"):
            template = read_packed_string(html.unescape(node.get("CProps", "")), "Template")
            if template in ALLOWED.values():
                stock.setdefault(template, []).append((int(node.get("X")), int(node.get("Y"))))
    return stock


def dedup(npcs: list[SpecialNpc], stock: dict[str, list[tuple[int, int]]]) -> list[SpecialNpc]:
    result: list[SpecialNpc] = []
    for npc in npcs:
        taken = stock.get(npc.template, []) + [(p.x, p.y) for p in result if p.template == npc.template]
        near = any(abs(npc.x - sx) <= DEDUP_RANGE and abs(npc.y - sy) <= DEDUP_RANGE for sx, sy in taken)
        if not near:
            result.append(npc)
    return result


def write_config(path: Path, npcs: list[SpecialNpc], skipped: int) -> None:
    lines = [
        "// Особые NPC Британии: лекари и стейблмастеры из World of Dream.",
        "// Сгенерировано tools/import_specials.py; править вручную не нужно.",
        f"// Всего: {len(npcs)} (отброшено дублей рядом со штатными узлами: {skipped}).",
        "",
    ]
    for i, npc in enumerate(npcs):
        lines += [
            f"Special {i}",
            "{",
            f"\tType\t\t{npc.template}",
            f"\tX\t\t{npc.x}",
            f"\tY\t\t{npc.y}",
            f"\tZ\t\t{npc.z}",
            "\tRealm\t\tbritannia",
            f"\tName\t\t{npc.name}",
            f"\tGender\t\t{npc.gender}",
            "}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wod", default=str(WOD_NPCS))
    parser.add_argument("--stock", default=str(STOCK_NODES))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    source = Path(args.wod)
    if not source.exists():
        print(f"ОШИБКА: не найден {source}")
        return 1

    npcs = parse_wod(source)
    by_type = {t: sum(1 for n in npcs if n.template == t) for t in ALLOWED.values()}
    print(f"WoD: {len(npcs)} NPC ({', '.join(f'{v} {k}' for k, v in by_type.items())})")

    stock_path = Path(args.stock)
    stock = parse_stock_nodes(stock_path) if stock_path.exists() else {}
    print(f"Штатные узлы: {', '.join(f'{len(v)} {k}' for k, v in stock.items()) or 'нет'}")

    kept = dedup(npcs, stock)
    skipped = len(npcs) - len(kept)
    print(f"После дедупликации (радиус {DEDUP_RANGE}): {len(kept)}, отброшено {skipped}")

    output = Path(args.output)
    if args.check:
        if not output.exists():
            print(f"ОШИБКА: нет {output}")
            return 1
        text = output.read_text(encoding="utf-8", errors="replace")
        count = len(re.findall(r"^Special\s+\d+", text, re.M))
        print(f"OK: {output}: {count} записей")
        return 0 if count == len(kept) else 1

    write_config(output, kept, skipped)
    print(f"Записано: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
