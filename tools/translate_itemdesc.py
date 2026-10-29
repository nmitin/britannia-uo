#!/usr/bin/env python3
"""Переводит только поле Desc в itemdesc.cfg, не трогая Name и остальное."""
import argparse, json, re, sys

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('mapping'); ap.add_argument('files', nargs='+')
    ap.add_argument('--dry-run', action='store_true')
    a=ap.parse_args()
    m=json.load(open(a.mapping,encoding='utf-8'))
    total=0
    for path in a.files:
        lines=open(path,encoding='utf-8',errors='replace').read().splitlines(True)
        out=[]; n=0
        for line in lines:
            mm=re.match(r'^(\s*Desc\s+)(.+?)(\s*)$', line.rstrip('\n'))
            if mm and mm.group(2) in m:
                ending='\n' if line.endswith('\n') else ''
                out.append(mm.group(1)+m[mm.group(2)]+ending)
                n+=1
            else:
                out.append(line)
        if n and not a.dry_run:
            open(path,'w',encoding='utf-8').writelines(out)
        total+=n
        print(f'{n:4d} {path}')
    print('всего замен:',total, '(dry-run)' if a.dry_run else '')

if __name__=='__main__': main()
