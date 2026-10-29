#!/usr/bin/env python3
"""Собирает Cliloc.rus для ClassicUO.

ClassicUO читает Cliloc.enu, затем накладывает Cliloc.<lang>. Поэтому файл
содержит только отличающиеся строки.

Источники перевода:
  * бинарный cliloc (например, перевод сообщества);
  * JSON {id: "текст"} или {english: "русский"}.

    python3 tools/build_cliloc_ru.py \
        --base client/Cliloc.enu \
        --translation cliloc_ru_community.enu \
        --out client/Cliloc.rus
"""
from __future__ import annotations

import argparse
import json
import struct
import sys


def parse_cliloc(path: str) -> dict[int, str]:
    data = open(path, "rb").read()
    if data[:1] == b"\x8e":
        raise SystemExit(f"{path}: BWT-сжатый cliloc пока не поддерживается")
    ver, unk = struct.unpack("<IH", data[:6])
    i = 6
    out: dict[int, str] = {}
    while i + 7 <= len(data):
        cid, flag, ln = struct.unpack("<IBH", data[i : i + 7])
        i += 7
        raw = data[i : i + ln]
        i += ln
        out[cid] = raw.rstrip(b"\x00").decode("utf-8", "replace")
    return out


def build(entries: dict[int, str], path: str) -> None:
    buf = bytearray(struct.pack("<IH", 2, 1))
    for cid in sorted(entries):
        text = entries[cid]
        if not text:
            continue
        b = text.encode("utf-8")
        if len(b) > 65535:
            continue
        buf += struct.pack("<IBH", cid, 0, len(b)) + b
    open(path, "wb").write(buf)
    print(f"Записано {len(entries)} строк в {path} ({len(buf)} байт)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="client/Cliloc.enu")
    ap.add_argument("--translation", default="", help="бинарный cliloc с переводом")
    ap.add_argument("--json", default="", help="JSON перевода")
    ap.add_argument("--out", default="client/Cliloc.rus")
    args = ap.parse_args()

    base = parse_cliloc(args.base)
    result: dict[int, str] = {}

    if args.translation:
        tr = parse_cliloc(args.translation)
        for cid, text in tr.items():
            if cid in base and text.strip() and text.strip() != base[cid].strip():
                result[cid] = text

    if args.json:
        with open(args.json, encoding="utf-8") as f:
            data = json.load(f)
        if all(isinstance(k, str) and not k.isdigit() for k in data):
            # словарь english -> russian
            rev = {v: k for k, v in base.items()}
            for en, ru in data.items():
                cid = rev.get(en)
                if cid is not None:
                    result[cid] = ru
        else:
            for cid, text in data.items():
                result[int(cid)] = text

    if not result:
        print("Нет перевода", file=sys.stderr)
        return 1
    build(result, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
