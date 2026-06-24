"""Arbeitsablauf — verbindet Notion-API und Kleinanzeigen-Suche.

Dies ist die EINZIGE Datei, die sowohl src/notion/ als auch
src/kleinanzeigen/ importiert.

Aufgaben:
  1. Suchparameter aus Notion-DB lesen
  2. Vorhandene Ergebnisse laden (Dublettenprüfung)
  3. Für jede Suchanfrage Kleinanzeigen durchsuchen
  4. Neue, preislich passende Artikel herausfiltern
  5. Ergebnisse in Notion-DB schreiben
"""

import time
import random
import sys

from .config import DB_SEARCH_ID, DB_RESULT_ID, load_token
from .logger import log, section, header, summary_line
from .filters import apply_all_filters
from .notion.client import query_database, create_page
from .notion.properties import extract_search_entry, build_result_properties
from .kleinanzeigen.search import fetch_kleinanzeigen
from .kleinanzeigen.text_utils import extract_plz_from_text


def get_existing_links(db_id, token=None):
    """Holt alle vorhandenen Ergebnis-Links aus der Ergebnis-DB.

    Returns:
        Set von URLs (normalisiert ohne trailing slash)
    """
    entries = query_database(db_id, token=token)
    from .notion.client import extract_property_value
    existing_links = set()

    for entry in entries:
        props = entry.get('properties', {})
        link = extract_property_value(props, 'Link')
        if link:
            existing_links.add(link.strip().rstrip('/'))

    log(f'  📋 {len(existing_links)} vorhandene Einträge in Ergebnis-DB')
    return existing_links


def run(dry_run=False, force=False):
    """Hauptfunktion: Führt die gesamte Such-Workflow aus.

    Args:
        dry_run: Wenn True, keine Notion-Schreiboperationen
        force:   Wenn True, überspringe die "vor kurzem gelaufen"-Prüfung
    """
    header('🔍 KLEINANZEIGEN SEARCH — Automatisierte Suche')

    if dry_run:
        log('⚙️  DRY RUN — Es werden keine Änderungen geschrieben', '  ')
    if force:
        log('⚡ FORCE-Modus — Überspringe Zeit-Prüfungen', '  ')

    # ─── Token laden ───
    token = load_token()
    log(f'Token OK: …{token[-8:]}', '  ')

    # ─── Schritt 1: Suchparameter aus DB1 lesen ───
    section('📖 Schritt 1: Lese Suchparameter aus DB „Artikel"')
    search_entries = query_database(DB_SEARCH_ID, token=token)
    log(f'✅ {len(search_entries)} Suchanfragen gefunden', '  ')

    if not search_entries:
        log('❌ Keine Suchanfragen in der Datenbank.')
        return

    # ─── Schritt 2: Vorhandene Links aus DB2 laden ───
    section('📖 Schritt 2: Lade vorhandene Ergebnisse aus DB „Gefunden Artikel"')
    existing_links = get_existing_links(DB_RESULT_ID, token=token)

    # ─── Schritt 3: Für jede Suchanfrage ausführen ───
    stats = {'total_new': 0, 'total_skipped': 0, 'total_errors': 0}

    for idx, entry in enumerate(search_entries):
        search = extract_search_entry(entry.get('properties', {}))
        name = search['name']
        max_price = search['max_price']
        ort = search['ort']
        umkreis = search['umkreis']

        # PLZ aus Ort extrahieren
        plz = extract_plz_from_text(ort) or ''

        section(f'📦 Suchanfrage {idx+1}/{len(search_entries)}: "{name}"')
        log(f'   Max-Preis: {max_price if max_price < 999999 else "—"} € '
            f'| Ort: {ort} → PLZ: {plz} '
            f'| Umkreis: {umkreis if umkreis else "—"} km')

        if not name:
            log('⚠  Überspringe: Kein Artikelname')
            continue

        # ─── Schritt 4: Kleinanzeigen-Suche ───
        log(f'🔎 Schritt 3: Suche auf Kleinanzeigen...')
        try:
            articles = fetch_kleinanzeigen(
                name,
                int(max_price) if max_price < 999999 else '',
                plz,
                int(umkreis) if umkreis else None,
            )
        except Exception as e:
            log(f'  ❌ Fehler bei der Suche: {e}')
            stats['total_errors'] += 1
            continue

        if not articles:
            log('  📭 Keine Artikel gefunden')
            continue

        # Distanz aus KA-Ergebnissen übernehmen
        for a in articles:
            a['distance'] = a.get('ka_distance')

        log(f'✅ {len(articles)} Artikel im Umkreis gefunden', '  ')

        # ─── Schritt 5: Filtern (Preis + Dubletten) ───
        section('🔍 Schritt 4: Filtere nach Preis & Dubletten')
        filtered, filter_stats = apply_all_filters(articles, max_price, existing_links)

        if filter_stats['price_skipped'] > 0:
            summary_line('Wegen Preis > Preislimit übersprungen',
                         filter_stats['price_skipped'], '⏭')
        if filter_stats['duplicate_skipped'] > 0:
            summary_line('Dubletten übersprungen',
                         filter_stats['duplicate_skipped'], '⏭')

        log(f'✅ {len(filtered)} neue Artikel zum Schreiben', '  ')
        stats['total_skipped'] += (
            filter_stats['price_skipped'] + filter_stats['duplicate_skipped']
        )

        # ─── Schritt 6: In Ergebnis-DB schreiben ───
        if not filtered:
            log('  💤 Nichts Neues für diese Suchanfrage')
            time.sleep(random.uniform(1.5, 3.0))
            continue

        section('💾 Schritt 5: Schreibe in Ergebnis-DB')

        for i, a in enumerate(filtered):
            name_val = a.get('name', '(kein Titel)')
            price_val = a.get('price')
            location = a.get('location', '') or ''
            distance = a.get('distance')
            link = a.get('url', '')

            props = build_result_properties(
                name=name_val,
                price=price_val,
                location=location,
                distance=distance,
                link=link,
            )

            if dry_run:
                dist_str = f', {distance}km' if distance is not None and distance >= 0 else ''
                log(f'  📝 [DRY RUN] {name_val} — {price_val}€ — {location}{dist_str}')
                stats['total_new'] += 1
            else:
                try:
                    result = create_page(DB_RESULT_ID, props, token=token)
                    if result:
                        stats['total_new'] += 1
                        dist_str = f', {distance}km' if distance is not None and distance >= 0 else ''
                        log(f'  ✅ [{i+1}/{len(filtered)}] {name_val} — '
                            f'{price_val}€ — {location}{dist_str}')
                        existing_links.add(link.strip().rstrip('/'))
                    else:
                        stats['total_errors'] += 1
                except RuntimeError as e:
                    log(f'  ❌ {e}')
                    stats['total_errors'] += 1

            if not dry_run:
                time.sleep(random.uniform(1.5, 3.0))

        # Pause zwischen Suchanfragen
        time.sleep(random.uniform(2.0, 5.0))

    # ─── Zusammenfassung ───
    header('📊 ZUSAMMENFASSUNG')
    summary_line('Suchanfragen verarbeitet', len(search_entries), '📦')
    summary_line('Neue Artikel hinzugefügt', stats['total_new'], '✅')
    summary_line('Dubletten / gefiltert', stats['total_skipped'], '⏭')
    summary_line('Fehler', stats['total_errors'], '❌')
    log('')
    log('✅ Fertig!')
    sys.stdout.flush()
