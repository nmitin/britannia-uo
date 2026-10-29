#!/usr/bin/env python3
"""Применяет перевод к строковым литералам в скриптах POL.

Формат словаря — JSON {"English text": "Русский текст"}. Переводятся только
точные совпадения целых литералов; комментарии не затрагиваются.

    python3 tools/apply_translation.py locale/ru/phrases.json --dry-run
    python3 tools/apply_translation.py locale/ru/phrases.json --only 'scripts/ai/*'
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys


def decode_escript(raw: str) -> str:
    return raw.replace('\\"', '"').replace("\\\\", "\\")


def encode_escript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def translate_source(src: str, mapping: dict[str, str]) -> tuple[str, int]:
    out: list[str] = []
    i = 0
    n = len(src)
    count = 0
    in_str = False
    in_line = False
    in_block = False
    buf: list[str] = []
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if in_line:
            out.append(c)
            if c == "\n":
                in_line = False
            i += 1
            continue
        if in_block:
            out.append(c)
            if c == "*" and nxt == "/":
                out.append(nxt)
                i += 2
                in_block = False
            else:
                i += 1
            continue
        if in_str:
            if c == "\\" and i + 1 < n:
                buf.append(c)
                buf.append(nxt)
                i += 2
                continue
            if c == '"':
                raw = "".join(buf)
                text = decode_escript(raw)
                if text in mapping:
                    out.append(encode_escript(mapping[text]))
                    count += 1
                else:
                    out.append(raw)
                out.append('"')
                in_str = False
                buf = []
                i += 1
                continue
            buf.append(c)
            i += 1
            continue
        if c == "/" and nxt == "/":
            out.append("//")
            i += 2
            in_line = True
            continue
        if c == "/" and nxt == "*":
            out.append("/*")
            i += 2
            in_block = True
            continue
        if c == '"':
            in_str = True
            buf = []
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out), count


def iter_sources(root: str):
    for base in ("scripts", "pkg"):
        top = os.path.join(root, base)
        if not os.path.isdir(top):
            continue
        for dirpath, _, names in os.walk(top):
            for name in names:
                if name.endswith((".src", ".inc")):
                    yield os.path.join(dirpath, name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mapping", help="JSON-словарь English -> Russian")
    ap.add_argument("--root", default="server")
    ap.add_argument("--only", default="*", help="glob по относительному пути файла")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default="")
    args = ap.parse_args()

    with open(args.mapping, encoding="utf-8") as f:
        mapping = json.load(f)
    if not isinstance(mapping, dict):
        print("Ожидается JSON-объект {english: russian}", file=sys.stderr)
        return 1

    total = 0
    files_changed = 0
    report = []
    for path in sorted(iter_sources(args.root)):
        rel = os.path.relpath(path, args.root)
        if not fnmatch.fnmatch(rel, args.only):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            src = f.read()
        new, count = translate_source(src, mapping)
        if count:
            total += count
            files_changed += 1
            report.append((rel, count))
            if not args.dry_run:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)

    for rel, count in report:
        print(f"{count:5d}  {rel}")
    print(f"\nЗаменено вхождений: {total}, файлов: {files_changed}")
    if args.dry_run:
        print("(режим проверки, файлы не изменены)")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(dict(report), f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
