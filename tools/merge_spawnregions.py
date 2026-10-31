#!/usr/bin/env python3
"""Аккуратно добавляет регионы спавна из World of Dream в ModernDistro.

Почему не копируем целиком: у WoD старый POL 098 и другие шаблоны NPC.
Скрипт берёт только те регионы, все группы которых либо уже есть в текущем
`defaultGroups.cfg`, либо полностью сопоставимы с текущими шаблонами NPC
по имени/ObjType. Регионы, которые сильно пересекаются с уже существующими,
по умолчанию пропускаются, чтобы не удваивать плотность spawn.

Использование:
    python3 tools/merge_spawnregions.py            # показать, что будет добавлено
    python3 tools/merge_spawnregions.py --apply    # записать изменения

После --apply перезапустить сервер. Скрипт идемпотентен: уже добавленные
регионы/группы повторно не добавляются.
"""
from __future__ import annotations

import argparse
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"

CURRENT_REGIONS = SERVER / "pkg/systems/spawnSystem/config/setup-britannia.cfg"
CURRENT_GROUPS = SERVER / "pkg/systems/spawnSystem/config/defaultGroups.cfg"
WOD_SPAWNS = ROOT / "src/WorldOfDream/pkg/world/spawners/regionspawner/regionspawn.cfg"
WOD_NPCS = ROOT / "src/WorldOfDream/pkg/npcs"


@dataclass(frozen=True)
class Region:
    name: str
    rect: tuple[int, int, int, int]
    groups: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class Template:
    full_name: str
    short_name: str
    objtype: int


def parse_regions(path: Path, key: str) -> list[Region]:
    text = path.read_text(encoding="utf-8", errors="replace")
    regions: list[Region] = []
    for name, body in re.findall(
        rf"^{key}\s+(.+?)\s*\{{(.*?)^\}}", text, re.S | re.M
    ):
        coords = re.search(
            r"(?:Coords|rect)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", body, re.M
        )
        if not coords:
            continue
        groups = tuple(
            (g, int(density))
            for g, density in re.findall(r"^\s*[Gg]roup\s+(\S+)\s+(\d+)", body, re.M)
        )
        regions.append(Region(name.strip(), tuple(map(int, coords.groups())), groups))
    return regions


def parse_current_groups(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"^Group\s+(\S+)\s*\{", text, re.M))


def parse_groups(path: Path) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    groups: dict[str, list[str]] = {}
    for name, body in re.findall(
        r"^[Gg]roup\s+(\S+)\s*\{(.*?)^\}", text, re.S | re.M
    ):
        groups[name] = re.findall(r"^\s*npc\s+(\S+)", body, re.M)
    return groups


def parse_npcdesc(paths: list[Path], prefix: str = "") -> list[Template]:
    templates: list[Template] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        pkg = path.parent.name
        for name, body in re.findall(
            r"^NpcTemplate\s+(\S+)\s*\{(.*?)^\}", text, re.S | re.M
        ):
            obj = re.search(r"^\s*ObjType\s+(0x[0-9A-Fa-f]+|\d+)", body, re.M)
            if not obj:
                continue
            templates.append(
                Template(
                    f"{prefix}{pkg}:{name}" if prefix else name,
                    name,
                    int(obj.group(1), 0),
                )
            )
    return templates


def build_template_maps() -> tuple[dict[str, str], dict[int, list[str]]]:
    current: list[Template] = []
    for path in [SERVER / "config/npcdesc.cfg", *SERVER.glob("pkg/**/npcdesc.cfg")]:
        if path.exists():
            current.extend(parse_npcdesc([path]))
    by_name = {t.short_name.lower(): t.short_name for t in current}
    by_obj: dict[int, list[str]] = defaultdict(list)
    for t in current:
        by_obj[t.objtype].append(t.short_name)
    return by_name, by_obj


def build_wod_template_map() -> dict[str, Template]:
    files = list(WOD_NPCS.rglob("npcdesc.cfg"))
    templates = parse_npcdesc(files, prefix="")
    return {t.full_name.lower(): t for t in templates}


def map_entry(
    entry: str, by_name: dict[str, str], by_obj: dict[int, list[str]], wod: dict[str, Template]
) -> str | None:
    short = entry.split(":")[-1].lower()
    if short in by_name:
        return by_name[short]
    old = wod.get(entry.lower())
    if old:
        candidates = by_obj.get(old.objtype, [])
        if len(candidates) == 1:
            return candidates[0]
    return None


def overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> int:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0, min(a[3], b[3]) - max(a[1], b[1])
    )


def area(r: tuple[int, int, int, int]) -> int:
    return max(0, r[2] - r[0]) * max(0, r[3] - r[1])


def format_group(name: str, entries: list[str]) -> str:
    lines = [f"Group {name}", "{", "\tEngine\tnpcFill"]
    for entry in entries:
        lines.append(f"\tEntry\t{entry}")
    lines.append("}")
    return "\n".join(lines)


def max_for_group(spawn: Region, density: int, cap: int) -> int:
    return min(max(1, int(area(spawn.rect) * density / 10000)), cap)


def format_region(name: str, spawn: Region, cap: int) -> str:
    lines = [f"Region {name}", "{", f"\tCoords\t{' '.join(map(str, spawn.rect))}", "\tSpawnWait\t120"]
    for group, density in spawn.groups:
        lines.append(f"\tGroup\t{group} {max_for_group(spawn, density, cap)}")
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="записать изменения")
    parser.add_argument("--overlap", type=float, default=0.3, help="макс. доля пересечения")
    parser.add_argument("--max-per-group", type=int, default=15, help="потолок spawn на группу")
    args = parser.parse_args()

    current_regions = parse_regions(CURRENT_REGIONS, "Region")
    current_groups = parse_current_groups(CURRENT_GROUPS)
    wod_regions = parse_regions(WOD_SPAWNS, "region")
    wod_groups = parse_groups(WOD_SPAWNS)

    by_name, by_obj = build_template_maps()
    wod_templates = build_wod_template_map()

    new_group_entries: dict[str, list[str]] = {}
    complete_groups: dict[str, bool] = {}
    for group, entries in wod_groups.items():
        if group in current_groups:
            complete_groups[group] = True
            continue
        mapped = [map_entry(e, by_name, by_obj, wod_templates) for e in entries]
        complete_groups[group] = bool(entries) and all(mapped)
        if complete_groups[group]:
            new_group_entries[group] = mapped  # type: ignore[assignment]

    current_rects = [r.rect for r in current_regions]
    existing_names = {r.name for r in current_regions}
    new_regions: list[tuple[str, Region]] = []
    for spawn in wod_regions:
        if not spawn.groups:
            continue
        if not all(complete_groups.get(g, False) for g, _ in spawn.groups):
            continue
        if area(spawn.rect) == 0:
            continue
        covered = sum(overlap(spawn.rect, r) for r in current_rects) / area(spawn.rect)
        if covered > args.overlap:
            continue
        name = f"wod_{spawn.name}"
        if name in existing_names:
            continue
        new_regions.append((name, spawn))

    # Добавляем только те новые группы, которые реально используются регионами.
    used_groups = {g for _, spawn in new_regions for g, _ in spawn.groups}
    new_group_entries = {g: e for g, e in new_group_entries.items() if g in used_groups}

    print(f"Текущих регионов: {len(current_regions)}, групп: {len(current_groups)}")
    print(f"Регионов WoD: {len(wod_regions)}, групп: {len(wod_groups)}")
    print(f"Новых групп: {len(new_group_entries)}, новых регионов: {len(new_regions)}")
    for name, spawn in new_regions:
        counts = [f"{g}={max_for_group(spawn, d, args.max_per_group)}" for g, d in spawn.groups]
        print(f"  {name}: {spawn.rect} -> {counts}")
    for group, entries in new_group_entries.items():
        print(f"  группа {group}: {entries}")

    if not args.apply:
        print("\nЭто dry-run. Для записи: --apply")
        return 0

    if not new_regions and not new_group_entries:
        print("Нечего добавлять.")
        return 0

    stamp = ".bak"
    shutil.copy2(CURRENT_REGIONS, CURRENT_REGIONS.with_suffix(CURRENT_REGIONS.suffix + stamp))
    shutil.copy2(CURRENT_GROUPS, CURRENT_GROUPS.with_suffix(CURRENT_GROUPS.suffix + stamp))

    if new_group_entries:
        text = CURRENT_GROUPS.read_text(encoding="utf-8")
        text += "\n\n// --- Добавлено из World of Dream (tools/merge_spawnregions.py) ---\n"
        for group, entries in new_group_entries.items():
            text += "\n" + format_group(group, entries) + "\n"
        CURRENT_GROUPS.write_text(text, encoding="utf-8")

    if new_regions:
        text = CURRENT_REGIONS.read_text(encoding="utf-8")
        text += "\n\n// --- Добавлено из World of Dream (tools/merge_spawnregions.py) ---\n"
        for name, spawn in new_regions:
            text += "\n" + format_region(name, spawn, args.max_per_group) + "\n"
        CURRENT_REGIONS.write_text(text, encoding="utf-8")

    print(f"\nЗаписано. Бэкапы: {CURRENT_REGIONS}.bak, {CURRENT_GROUPS}.bak")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
