#!/usr/bin/env python3
"""Извлекает строковые литералы из скриптов POL в каталог для перевода.

Использование:
    python3 tools/extract_strings.py [--root server] [--out locale/ru/catalog.json]

Каталог содержит все строки в кавычках с файлом и строкой. Поле "user_facing"
выставлено эвристикой: строка похожа на сообщение игроку, а не на ключ,
путь или технический идентификатор.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter

STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def strip_comments_keep_lines(text: str) -> str:
    """Заменяет комментарии пробелами, сохраняя переводы строк и позиции."""
    out = []
    i = 0
    n = len(text)
    in_line = False
    in_block = False
    in_str = False
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_line:
            if c == "\n":
                in_line = False
                out.append(c)
            else:
                out.append(" ")
            i += 1
            continue
        if in_block:
            if c == "*" and nxt == "/":
                out.append("  ")
                i += 2
                in_block = False
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
            continue
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == "/" and nxt == "/":
            out.append("  ")
            i += 2
            in_line = True
            continue
        if c == "/" and nxt == "*":
            out.append("  ")
            i += 2
            in_block = True
            continue
        if c == '"':
            in_str = True
        out.append(c)
        i += 1
    return "".join(out)


def looks_user_facing(s: str) -> bool:
    if not s or len(s) < 2:
        return False
    if not re.search(r"[A-Za-zА-Яа-яЁё]", s):
        return False
    # технические ключи, пути, идентификаторы
    if re.fullmatch(r"[A-Za-z0-9_.:/#\-]+", s):
        return False
    if "::" in s or s.startswith(":") or s.startswith("#"):
        return False
    if re.search(r"\.(src|inc|ecl|cfg|mul|txt)$", s, re.I):
        return False
    # сообщения обычно содержат пробел или знак препинания
    if " " in s or re.search(r"[.!?,:]", s):
        return True
    # одиночное слово с заглавной буквы — вероятно имя/название
    return bool(re.match(r"^[A-ZА-ЯЁ][a-zа-яё]+$", s))


def iter_sources(root: str):
    for base in ("scripts", "pkg"):
        top = os.path.join(root, base)
        if not os.path.isdir(top):
            continue
        for dirpath, _, filenames in os.walk(top):
            for name in filenames:
                if name.endswith((".src", ".inc")):
                    yield os.path.join(dirpath, name)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="server", help="каталог дистрибутива POL")
    ap.add_argument("--out", default="locale/ru/catalog.json")
    args = ap.parse_args()

    rows = []
    for path in sorted(iter_sources(args.root)):
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        clean = strip_comments_keep_lines(raw)
        # номер строки по позиции
        line_starts = [0]
        for m in re.finditer("\n", clean):
            line_starts.append(m.end())
        for m in STRING_RE.finditer(clean):
            text = m.group(1)
            if not text.strip():
                continue
            import bisect

            line = bisect.bisect_right(line_starts, m.start())
            rows.append(
                {
                    "file": os.path.relpath(path, args.root),
                    "line": line,
                    "text": text,
                    "user_facing": looks_user_facing(text),
                }
            )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    uf = [r for r in rows if r["user_facing"]]
    unique_uf = {r["text"] for r in uf}
    print(f"Всего литералов: {len(rows)}")
    print(f"Похожи на сообщения: {len(uf)} ({len(unique_uf)} уникальных)")
    print(f"Каталог: {args.out}")

    by_file = Counter(r["file"] for r in uf)
    print("\nТоп файлов по числу сообщений:")
    for f, c in by_file.most_common(20):
        print(f"{c:5d}  {f}")


if __name__ == "__main__":
    main()
