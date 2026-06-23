"""Arbeitsablauf — verbindet Notion-API und Kleinanzeigen-Suche.

Dies ist die EINZIGE Datei, die sowohl src/notion/ als auch
src/kleinanzeigen/ importiert.
"""

import time
import datetime
import random
import sys

from .config import DB_SEARCH_ID, DB_RESULT_ID, load_token
from .notion.client import (
    query_database, extract_property_value, create_page,
)
from .kleinanzeigen.search import fetch_kleinanzeigen
from .kleinanzeigen.geo import get_plz_coords, haversine, extract_plz_from_text


def log(msg):
    """Einheitliche Log-Ausgabe mit Zeitstempel."""
    ts = time.strftime('%H:%M:%S')
    print(f'[{ts}] {msg}')
    sys.stdout.flush()


def get_existing_links(db_id, token=None):
    """Holt alle vorhandenen Ergebnis-Links aus der Ergebnis-DB.

    Gibt ein Set von URLs zurück.
    """
    entries = query_database(db_id, token=token)
    existing_links = set()

    for entry in entries:
        props = entry.get('properties', {})
        link = extract_property_value(props, 'Link')
        if link:
            existing_links.add(link.strip().rstrip('/'))

    log(f'  📋 {len(existing_links)} vorhandene Einträge in Ergebnis-DB')
    return existing_links


def filter_by_distance(articles, search_plz, max_radius_km):
    """Filtert Artikel nach maximaler Entfernung (Luftlinie) zur Such-PLZ.

    Berechnet die Entfernung für jeden Artikel.
    Bevorzugt Kleinanzeigens eigene Distanzangabe (genauer).
    Gibt Artikel mit berechneter Entfernung zurück.
    """
    if not search_plz or not max_radius_km:
        return articles

    search_coords = get_plz_coords(search_plz)
    filtered = []

    for a in articles:
        # Kleinanzeigen-eigene Distanz bevorzugen (genauer)
        ka_dist = a.get('ka_distance')
        if ka_dist is not None:
            a['distance'] = ka_dist
            if ka_dist <= max_radius_km:
                filtered.append(a)
            else:
                a['_skipped_reason'] = (
                    f'Entfernung {ka_dist}km > {max_radius_km}km (KA-Angabe)'
                )
            continue

        # Fallback: PLZ aus dem Artikel extrahieren und Haversine rechnen
        plz = a.get('location_plz')
        if not plz:
            plz = extract_plz_from_text(a.get('location', ''))
            if plz:
                a['location_plz'] = plz

        if plz:
            item_coords = get_plz_coords(plz)
            distance = haversine(
                search_coords[0], search_coords[1],
                item_coords[0], item_coords[1]
            )
            a['distance'] = distance

            if distance <= max_radius_km:
                filtered.append(a)
            else:
                a['_skipped_reason'] = (
                    f'Entfernung {distance}km > {max_radius_km}km'
                )
        else:
            # Keine PLZ → trotzdem aufnehmen, Entfernung auf -1
            a['distance'] = -1
            a['_skipped_reason'] = 'Keine PLZ im Artikel gefunden'
            filtered.append(a)

    return filtered


def run(dry_run=False):
    """Hauptfunktion: Führt die gesamte Such-Workflow aus.

    1. Suchparameter aus DB lesen
    2. Vorhandene Ergebnisse laden (Dublettenprüfung)
    3. Für jede Suchanfrage Kleinanzeigen durchsuchen
    4. Nach Entfernung filtern
    5. Dubletten und Preis prüfen
    6. Neue Ergebnisse in DB schreiben

    Args:
        dry_run: Wenn True, keine Notion-Schreiboperationen ausführen
    """
    log('═' * 60)
    log('🔍 KLEINANZEIGEN SEARCH — Automatisierte Suche')
    log('═' * 60)

    if dry_run:
        log('⚙️  DRY RUN — Es werden keine Änderungen geschrieben')

    # Token laden
    token = load_token()
    log(f'  Token OK: {token[:10]}...{token[-4:]}')

    # ─── Schritt 1: Suchparameter aus DB1 lesen ───
    log('')
    log('📖 Schritt 1: Lese Suchparameter aus DB "Artikel"...')
    search_entries = query_database(DB_SEARCH_ID, token=token)
    log(f'  ✅ {len(search_entries)} Suchanfragen gefunden')

    if not search_entries:
        log('❌ Keine Suchanfragen in der Datenbank.')
        return

    # ─── Schritt 2: Vorhandene Links aus DB2 laden ───
    log('')
    log('📖 Schritt 2: Lade vorhandene Ergebnisse aus DB "Gefunden Artikel"...')
    existing_links = get_existing_links(DB_RESULT_ID, token=token)

    # ─── Schritt 3: Für jede Suchanfrage ausführen ───
    total_new = 0
    total_skipped = 0
    total_errors = 0

    for idx, entry in enumerate(search_entries):
        props = entry.get('properties', {})

        artikelname = extract_property_value(props, 'Artikelname') or ''
        max_price = extract_property_value(props, 'Preis')
        ort = extract_property_value(props, 'Ort') or ''
        plz = extract_plz_from_text(ort) or ''
        umkreis = extract_property_value(props, 'Umkreis')

        log('')
        log('─' * 50)
        log(f'📦 Suchanfrage {idx+1}/{len(search_entries)}: "{artikelname}"')
        log(f'   Max-Preis: {max_price} € | Ort: {ort} → PLZ: {plz} | Umkreis: {umkreis} km')

        if not artikelname:
            log('⚠  Überspringe: Kein Artikelname')
            continue

        # Preis normalisieren
        if max_price is not None:
            try:
                max_price = float(max_price)
            except (ValueError, TypeError):
                max_price = 999999
        else:
            max_price = 999999

        # Umkreis normalisieren
        if umkreis is not None:
            try:
                radius_km = float(umkreis)
            except (ValueError, TypeError):
                radius_km = None
        else:
            radius_km = None

        # ─── Schritt 4: Kleinanzeigen-Suche ───
        log(f'🔎 Schritt 3: Suche auf Kleinanzeigen...')
        try:
            articles = fetch_kleinanzeigen(
                artikelname,
                int(max_price) if max_price < 999999 else '',
                plz,
                int(radius_km) if radius_km else None,
            )
        except Exception as e:
            log(f'  ❌ Fehler bei der Suche: {e}')
            total_errors += 1
            continue

        if not articles:
            log('  📭 Keine Artikel gefunden')
            continue

        # ─── Schritt 5: Nach Entfernung filtern ───
        if plz and radius_km:
            log(f'📍 Schritt 4: Filtere nach Entfernung (≤{radius_km}km von {plz})...')
            articles = filter_by_distance(articles, plz, radius_km)
            before = len(articles)
            articles_filtered = [
                a for a in articles
                if '_skipped_reason' not in a
                or 'Entfernung' not in a.get('_skipped_reason', '')
            ]
            removed_count = before - len(articles_filtered)
            if removed_count > 0:
                log(f'  🗑 {removed_count} Artikel wegen Entfernung >{radius_km}km entfernt')
                for a in articles:
                    if '_skipped_reason' in a and 'Entfernung' in a['_skipped_reason']:
                        log(f'    ↳ {a.get("name", "?")} — {a["_skipped_reason"]}')
            articles = articles_filtered

        log(f'  ✅ {len(articles)} Artikel im Umkreis')

        # ─── Schritt 6: Dubletten-Prüfung & Preis-Filter ───
        log(f'🔍 Schritt 5: Prüfe auf Dubletten und Preis...')
        new_articles = []
        skipped_duplicates = 0
        skipped_price = 0

        for a in articles:
            url = a.get('url', '').strip().rstrip('/')
            price = a.get('price')
            name = a.get('name', '(kein Titel)')

            # Preis-Check
            if price is not None and max_price < 999999 and price > max_price:
                skipped_price += 1
                continue

            # Dubletten-Check (anhand URL)
            if url and url in existing_links:
                skipped_duplicates += 1
                continue

            new_articles.append(a)

        log(f'  ✅ {len(new_articles)} neue Artikel')
        if skipped_duplicates > 0:
            log(f'  ⏭ {skipped_duplicates} Dubletten übersprungen')
            total_skipped += skipped_duplicates
        if skipped_price > 0:
            log(f'  ⏭ {skipped_price} wegen Preis >{max_price}€ übersprungen')

        # ─── Schritt 7: In Ergebnis-DB schreiben ───
        if new_articles:
            log(f'💾 Schritt 6: Schreibe {len(new_articles)} neue Artikel in Ergebnis-DB...')

            for i, a in enumerate(new_articles):
                name = a.get('name', '(kein Titel)')[:80]
                price_val = a.get('price')
                location = (
                    a.get('location', '')[:30]
                    if a.get('location') else ''
                )
                distance = a.get('distance', -1)
                link = a.get('url', '')

                # Notion-Properties
                properties = {
                    'Artikelname': {
                        'title': [{'text': {'content': name}}],
                    },
                    'Preis': {
                        'number': price_val if price_val is not None else None,
                    },
                    'Ort': {
                        'rich_text': [{'text': {'content': location}}],
                    },
                    'Entfernung': {
                        'number': distance if distance >= 0 else None,
                    },
                    'Link': {
                        'url': link if link else None,
                    },
                    'Gefunden am': {
                        'date': {
                            'start': datetime.datetime.now().isoformat(),
                        },
                    },
                }

                if dry_run:
                    log(
                        f'  📝 [DRY RUN] {name} — {price_val}€ — '
                        f'{location}{", " + str(distance) + "km" if distance >= 0 else ""}'
                    )
                    total_new += 1
                else:
                    try:
                        result = create_page(DB_RESULT_ID, properties, token=token)
                        if result:
                            total_new += 1
                            dist_str = f', {distance}km' if distance >= 0 else ''
                            log(
                                f'  ✅ [{i+1}/{len(new_articles)}] {name} — '
                                f'{price_val}€ — {location}{dist_str}'
                            )
                            existing_links.add(link)
                        else:
                            total_errors += 1
                    except RuntimeError as e:
                        log(f'  ❌ {e}')
                        total_errors += 1

                if not dry_run:
                    time.sleep(random.uniform(1.5, 3.0))
        else:
            log('  💤 Nichts Neues für diese Suchanfrage')

        # Pause zwischen Suchanfragen
        time.sleep(random.uniform(3.0, 6.0))

    # ─── Zusammenfassung ───
    log('')
    log('═' * 60)
    log('📊 ZUSAMMENFASSUNG')
    log('═' * 60)
    log(f'  Suchanfragen verarbeitet: {len(search_entries)}')
    log(f'  Neue Artikel hinzugefügt: {total_new}')
    log(f'  Dubletten übersprungen:   {total_skipped}')
    log(f'  Fehler:                   {total_errors}')
    log('═' * 60)
    log('✅ Fertig!')
