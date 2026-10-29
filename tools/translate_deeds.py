#!/usr/bin/env python3
"""Генерирует переводы '<base> deed' и 'deed to <base>' из готовых словарей."""
import json, glob, re

mapping={}
for p in glob.glob('locale/ru/itemdesc_*.json'):
    mapping.update(json.load(open(p,encoding='utf-8')))

def base_variants(s):
    s=s.strip()
    yield s
    for pref in ('a ', 'an ', 'the '):
        if s.lower().startswith(pref): yield s[len(pref):]

out={}
for en, ru in mapping.items():
    pass
# соберём все Desc из itemdesc
descs=set()
for f in glob.glob('server/pkg/**/config/itemdesc.cfg',recursive=True)+['server/config/itemdesc.cfg']:
    for line in open(f,encoding='utf-8',errors='replace'):
        m=re.match(r'^(\s*)Desc\s+(.+?)\s*$',line)
        if m and not re.search(r'[А-Яа-яЁё]',m.group(2)): descs.add(m.group(2))

for d in descs:
    found=None
    if d.endswith(' deed'):
        base=d[:-5].strip()
        for v in base_variants(base):
            if v in mapping: found=mapping[v]; break
    elif d.startswith('deed to '):
        base=d[8:].strip()
        for v in base_variants(base):
            if v in mapping: found=mapping[v]; break
    if found:
        out[d] = 'документ: ' + found
json.dump(out,open('locale/ru/itemdesc_deeds.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('сгенерировано переводов deed:',len(out))
