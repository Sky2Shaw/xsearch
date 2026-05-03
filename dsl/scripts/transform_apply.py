#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, yaml
from pathlib import Path

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def dump(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, width=1000)

def select_from_list(items, key):
    for item in items:
        if isinstance(item, dict) and (item.get('name') == key or item.get('id') == key):
            return item
    raise KeyError(f'list item [{key}] not found')

def resolve_parent(obj, path):
    parts=path.split('.')
    cur=obj
    for part in parts[:-1]:
        if '[' in part and part.endswith(']'):
            field, key = part[:-1].split('[',1)
            cur=cur[field]
            cur=select_from_list(cur, key)
        else:
            cur=cur[part]
    return cur, parts[-1]

def get_path(obj, path):
    cur=obj
    for part in path.split('.'):
        if '[' in part and part.endswith(']'):
            field, key = part[:-1].split('[',1)
            cur=select_from_list(cur[field], key)
        else:
            cur=cur[part]
    return cur

def set_path(obj, path, value):
    parent,last=resolve_parent(obj,path)
    if '[' in last and last.endswith(']'):
        raise ValueError('cannot assign directly to a list selector; assign to a field below it')
    parent[last]=value

def main():
    ap=argparse.ArgumentParser(description='Apply an ATDSL transform_trace to a base atdsl.instance.')
    ap.add_argument('--base', required=True)
    ap.add_argument('--transform', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--strict-old', action='store_true')
    args=ap.parse_args()
    base=load(args.base)
    tr=load(args.transform)
    out=copy.deepcopy(base)
    applied=[]
    for mut in tr.get('mutations', []):
        path=mut['path']
        old=get_path(out,path)
        if args.strict_old and 'old' in mut and old != mut['old']:
            raise SystemExit(f'old value mismatch at {path}: actual={old!r} expected={mut["old"]!r}')
        set_path(out,path,mut.get('new'))
        applied.append({'path':path,'old':old,'new':mut.get('new')})
    out.setdefault('metadata', {})['last_transform_applied']={'id':tr.get('id'),'mutations':applied}
    dump(args.out, out)
    print(f'applied {tr.get("id")} mutations={len(applied)} -> {args.out}')
if __name__ == '__main__':
    main()
