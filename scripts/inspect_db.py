#!/usr/bin/env python
"""Notion-DB-Inspektion: Zeigt Schema und Einträge beider Datenbanken an.

Usage:
    python scripts/inspect_db.py
"""

import sys
import os

# Projekt-Root zum Python-Pfad hinzufügen
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import NOTION_VERSION, BASE_URL, PAGE_SIZE, DB_SEARCH_ID, DB_RESULT_ID, load_token
from src.notion.client import notion_get, notion_post


def show_schema(db_id, label):
    """Zeigt das Schema einer Notion-Datenbank an."""
    print()
    print('=' * 70)
    print(f'  DATABASE SCHEMA: {label}')
    print(f'  ID: {db_id}')
    print('=' * 70)

    status, data = notion_get(f'databases/{db_id}')
    if status >= 400 or data.get('object') == 'error':
        print('  Cannot retrieve database schema')
        return

    title_parts = data.get('title', [])
    title = ''.join(t.get('plain_text', '') for t in title_parts)
    print(f'  Title: "{title}"')
    print(f'  Object: {data.get("object", "?")}')

    ds = data.get('data_sources', [])
    if ds:
        print(f'  Data source: {ds[0].get("id", "?")} ({ds[0].get("name", "?")})')

    props = data.get('properties', {})
    print(f'\n  Properties: {len(props)}')
    if not props:
        print('  (WARNING: No properties returned - API may not support')
        print('   schema retrieval for this database type)')
        print(f'  Response keys: {list(data.keys())}')
        return

    for name, prop in props.items():
        ptype = prop.get('type', '?')
        print(f'    [{ptype:16s}]  {name}')
        if ptype in ('select', 'multi_select', 'status'):
            opts = prop.get(ptype, {}).get('options', [])
            if opts:
                for o in opts:
                    print(f'      -> {o.get("name", "?")} ({o.get("color", "")})')
        elif ptype == 'relation':
            print(f'      -> DB: {prop.get("relation", {}).get("database_id", "?")}')
        elif ptype == 'formula':
            print(f'      expr: {prop.get("formula", {}).get("expression", "?")}')


def show_entries(db_id, label):
    """Zeigt die Einträge einer Notion-Datenbank an."""
    print()
    print('=' * 70)
    print(f'  DATABASE ENTRIES: {label}')
    print(f'  ID: {db_id}')
    print('=' * 70)

    status, data = notion_post(f'databases/{db_id}/query',
                                {'page_size': PAGE_SIZE})
    if status >= 400 or data.get('object') == 'error':
        print('  Cannot query entries')
        return

    results = data.get('results', [])
    has_more = data.get('has_more', False)
    next_cursor = data.get('next_cursor')
    print(f'  Results: {len(results)} | has_more: {has_more} | next: {next_cursor}')

    if not results:
        print('  (no entries)')
        return

    for idx, entry in enumerate(results):
        print(f'\n  --- Entry {idx+1} ---')
        eid = entry.get('id', '?')
        print(f'  ID: {eid}')
        print(f'  Created: {entry.get("created_time", "?")}')
        print(f'  Updated: {entry.get("last_edited_time", "?")}')

        entry_props = entry.get('properties', {})
        if not entry_props:
            print('  (no properties)')
            continue

        for pname, pval in entry_props.items():
            ptype = pval.get('type', '?')

            if ptype == 'title':
                val = ''.join(t.get('plain_text', '')
                             for t in pval.get('title', []))
            elif ptype == 'rich_text':
                val = ''.join(t.get('plain_text', '')
                             for t in pval.get('rich_text', []))
            elif ptype == 'select':
                s = pval.get('select')
                val = s['name'] if s else '(none)'
            elif ptype == 'multi_select':
                items = [s['name'] for s in pval.get('multi_select', [])]
                val = ', '.join(items) if items else '(none)'
            elif ptype == 'number':
                val = pval.get('number', '-')
            elif ptype == 'checkbox':
                val = pval.get('checkbox', '?')
            elif ptype == 'date':
                d = pval.get('date')
                val = f'{d["start"]} -> {d.get("end", "")}' if d else '(none)'
            elif ptype == 'url':
                val = pval.get('url', '-')
            elif ptype == 'email':
                val = pval.get('email', '-')
            elif ptype == 'phone_number':
                val = pval.get('phone_number', '-')
            elif ptype == 'status':
                s = pval.get('status')
                val = s['name'] if s else '(none)'
            elif ptype == 'formula':
                f = pval.get('formula', {})
                ftype = f.get('type', '?')
                val = f.get(ftype, str(f))
            elif ptype == 'relation':
                rels = [r['id'] for r in pval.get('relation', [])]
                val = ', '.join(rels) if rels else '(none)'
            elif ptype == 'rollup':
                r = pval.get('rollup', {})
                rtype = r.get('type', '?')
                val = r.get(rtype, str(r))
            elif ptype in ('created_by', 'last_edited_by'):
                u = pval.get(ptype, {})
                val = u.get('name', u.get('id', '?'))
            elif ptype in ('created_time', 'last_edited_time'):
                val = pval.get(ptype, '?')
            elif ptype == 'files':
                files = [f.get('name', '?') for f in pval.get('files', [])]
                val = ', '.join(files) if files else '(none)'
            elif ptype == 'people':
                people = [p.get('name', p.get('id', '?'))
                         for p in pval.get('people', [])]
                val = ', '.join(people) if people else '(none)'
            else:
                val = pval.get(ptype, str(pval)[:100])

            print(f'    [{ptype:16s}]  {pname}: {val}')

    print(f'\n  Total entries returned: {len(results)}')
    if has_more:
        print(f'  NOTE: More entries available (next_cursor: {next_cursor})')


def main():
    token = load_token()
    print(f'Token: {token[:10]}...{token[-4:]} ({len(token)} chars)')
    print(f'API version: {NOTION_VERSION}')
    print()

    show_schema(DB_SEARCH_ID, '"Artikel" (Suchanfragen)')
    show_schema(DB_RESULT_ID, '"Gefunden Artikel" (Ergebnisse)')

    print()
    print('=' * 70)
    print('  QUERYING ENTRIES')
    print('=' * 70)

    show_entries(DB_SEARCH_ID, '"Artikel" (Suchanfragen)')
    show_entries(DB_RESULT_ID, '"Gefunden Artikel" (Ergebnisse)')

    print()
    print('=' * 70)
    print('  DONE')
    print('=' * 70)


if __name__ == '__main__':
    main()
