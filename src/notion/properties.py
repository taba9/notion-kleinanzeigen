"""Notion-Property-Builder für die Kleinanzeigen-Datenbanken.

Stellt Factory-Funktionen bereit, die Property-Dicts im Notion-API-Format
für die bekannten DB-Schemata bauen. Zentralisiert die Schema-Kenntnis,
damit Änderungen an der DB-Struktur nur hier angepasst werden müssen.

Such-DB „Artikel" (ID: d2901790-…):
  - Artikelname (title)
  - Preis (number)
  - Ort (rich_text)     — PLZ oder Ort
  - Umkreis (number)    — in km

Ergebnis-DB „Gefunden Artikel" (ID: 388231b1-…):
  - Artikelname (title)
  - Preis (number)
  - Ort (rich_text)
  - Entfernung (number) — in km
  - Link (url)
  - Gefunden am (date)
"""

import datetime
from .client import extract_property_value


# ─── Extraktion aus Such-DB ──────────────────────────────────


def extract_search_entry(props):
    """Extrahiert eine Suchanfrage aus den Properties der Such-DB.

    Args:
        props: Notion-Properties-Dict eines DB-Eintrags

    Returns:
        Dict mit Keys: name, max_price, ort, umkreis
    """

    name = extract_property_value(props, 'Artikelname') or ''
    max_price = extract_property_value(props, 'Preis')
    ort = extract_property_value(props, 'Ort') or ''
    umkreis = extract_property_value(props, 'Umkreis')

    # Preise normalisieren
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
            umkreis = float(umkreis)
        except (ValueError, TypeError):
            umkreis = None

    return {
        'name': name,
        'max_price': max_price,
        'ort': ort,
        'umkreis': umkreis,
    }


# ─── Builder für Ergebnis-DB ─────────────────────────────────


def build_result_properties(name, price, location, distance, link):
    """Baut die Properties für einen Eintrag in der Ergebnis-DB.

    Args:
        name: Artikelname (max 80 Zeichen)
        price: Preis als Zahl oder None
        location: Ort als String
        distance: Entfernung in km oder None
        link: URL zum Artikel

    Returns:
        Dict im Notion-API-Properties-Format
    """
    # Entfernung normalisieren: nur positive Werte setzen
    dist_val = distance if (distance is not None and distance >= 0) else None

    return {
        'Artikelname': {
            'title': [{'text': {'content': name[:80]}}],
        },
        'Preis': {
            'number': price if price is not None else None,
        },
        'Ort': {
            'rich_text': [{'text': {'content': location[:30]}}],
        },
        'Entfernung': {
            'number': dist_val,
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
