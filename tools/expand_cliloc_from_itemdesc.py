#!/usr/bin/env python3
"""Переносит переводы Desc из itemdesc в Cliloc по совпадению английского текста."""
import json, re, struct, glob, sys

def parse(path):
    d=open(path,'rb').read(); i=6; out={}
    while i+7<=len(d):
        cid,fl,ln=struct.unpack('<IBH',d[i:i+7]); i+=7
        out[cid]=d[i:i+ln].decode('utf-8','replace'); i+=ln
    return out

def norm(s):
    s=s.strip()
    s=re.sub(r'^an?\s+', '', s, flags=re.I)
    s=s.rstrip('.')
    return s.strip().lower()

base=parse('client/Cliloc.enu')
mapping={}
for p in glob.glob('locale/ru/itemdesc_*.json'):
    mapping.update(json.load(open(p,encoding='utf-8')))
norm_map={norm(k):v for k,v in mapping.items()}
# также точные формы без нормализации
for k,v in mapping.items(): norm_map.setdefault(k.strip().lower(),v)

out={}
for cid,text in base.items():
    n=norm(text)
    if n in norm_map:
        out[str(cid)]=norm_map[n]
json.dump(out,open('locale/ru/cliloc_from_items.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('сопоставлено cliloc-записей:',len(out),'из',len(mapping),'переводов')
