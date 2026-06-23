#!/usr/bin/env python
"""
Automatisierte Kleinanzeigen-Suche mit Notion-Datenbank-Anbindung.
Liest Suchparameter (Artikelname, Max-Preis, PLZ, Umkreis) aus einer Notion-DB,
sucht auf Kleinanzeigen mit korrektem Radius-Filter,
berechnet Entfernungen,
prüft auf Dubletten,
und schreibt neue Ergebnisse in eine Ergebnis-Notion-DB.

Notion-API-Version: 2022-06-28 (zwingend erforderlich für diese DBs)
"""

import json
import urllib.request
import urllib.error
import re
import math
import time
import os
import sys
import datetime
import random

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ─── Konfiguration ───────────────────────────────────────────────────────────

NOTION_VERSION = '2022-06-28'
BASE_URL = 'https://api.notion.com/v1'
PAGE_SIZE = 100

# Datenbank-IDs
DB_SEARCH_ID = 'd2901790-6cd9-4c9f-b949-7c93e6987be7'    # "Artikel" (Suchanfragen)
DB_RESULT_ID = '388231b1-2b4e-806d-b628-f542c39c2f19'     # "Gefunden Artikel" (Ergebnisse)

# Kleinanzeigen
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# User-Agent Rotation – bei 403 oder regelmäßig wechseln
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]
KA_BASE = 'https://www.kleinanzeigen.de'

# ─── PLZ → Koordinaten (approximative Mittelpunkte der PLZ-Gebiete) ─────────
# Datenquelle: Generische Approximation basierend auf deutschen PLZ-Bereichen
# Genauigkeit ca. 10-30km, ausreichend für Umkreis-Filterung
PLZ_COORDS = {
    # 01xxx - Dresden/Ostsachsen
    '01': (51.05, 13.74),
    '02': (51.15, 14.00),
    '03': (51.50, 14.00),
    '04': (51.35, 12.40),
    '05': (51.85, 12.25),
    '06': (51.55, 12.00),
    '07': (50.80, 12.10),
    '08': (50.65, 12.40),
    '09': (50.75, 12.80),
    # 1xxxx - Berlin/Brandenburg
    '10': (52.52, 13.41),  # Berlin
    '11': (52.50, 13.50),
    '12': (52.45, 13.45),
    '13': (52.55, 13.30),
    '14': (52.40, 13.10),
    '15': (52.25, 14.00),
    '16': (52.00, 14.00),
    '17': (53.10, 13.50),
    '18': (54.10, 12.20),
    '19': (53.60, 11.40),
    # 2xxxx - Hamburg/Nordwest
    '20': (53.55, 10.00),  # Hamburg
    '21': (53.45, 10.20),
    '22': (53.60, 10.00),
    '23': (53.85, 10.70),
    '24': (54.30, 10.10),
    '25': (53.90, 9.50),
    '26': (53.30, 7.90),
    '27': (53.50, 8.50),
    '28': (53.10, 8.80),
    '29': (52.80, 10.10),
    # 3xxxx - Niedersachsen/Hessen
    '30': (52.37, 9.74),   # Hannover
    '31': (52.30, 9.80),
    '32': (52.20, 8.80),
    '33': (52.00, 8.50),
    '34': (51.30, 9.50),
    '35': (50.60, 8.70),
    '36': (50.80, 9.80),
    '37': (51.50, 10.00),
    '38': (52.00, 10.50),
    '39': (52.10, 11.00),
    # 4xxxx - NRW
    '40': (51.23, 6.78),   # Düsseldorf
    '41': (51.20, 6.80),
    '42': (51.15, 7.00),
    '43': (51.10, 6.80),
    '44': (51.50, 7.30),
    '45': (51.45, 7.00),
    '46': (51.50, 6.80),
    '47': (51.40, 6.50),
    '48': (51.90, 6.90),
    '49': (52.20, 8.00),
    # 5xxxx - Köln/Rheinland-Pfalz
    '50': (50.94, 6.96),   # Köln
    '51': (50.95, 7.00),
    '52': (50.80, 6.30),
    '53': (50.70, 7.10),
    '54': (50.00, 6.80),
    '55': (49.90, 7.70),
    '56': (50.35, 7.50),
    '57': (50.90, 7.90),
    '58': (51.30, 7.50),
    '59': (51.60, 7.80),
    # 6xxxx - Hessen/BaWü
    '60': (50.12, 8.68),   # Frankfurt
    '61': (50.20, 8.70),
    '62': (49.50, 8.50),
    '63': (50.00, 8.90),
    '64': (49.80, 8.60),
    '65': (50.00, 8.20),
    '66': (49.30, 7.00),
    '67': (49.50, 8.10),
    '68': (49.50, 8.45),
    '69': (49.50, 8.60),
    # 7xxxx - Baden-Württemberg
    '70': (48.78, 9.18),   # Stuttgart
    '71': (48.80, 9.20),
    '72': (48.50, 9.00),
    '73': (48.70, 9.60),
    '74': (49.10, 9.20),
    '75': (48.90, 8.70),
    '76': (49.00, 8.40),
    '77': (48.55, 7.90),
    '78': (47.90, 8.30),
    '79': (48.00, 7.85),
    # 8xxxx - Bayern (Süd)
    '80': (48.14, 11.58),  # München
    '81': (48.10, 11.60),
    '82': (47.55, 11.00),
    '83': (47.80, 12.30),
    '84': (48.55, 12.15),
    '85': (48.20, 11.70),
    '86': (48.60, 10.80),
    '87': (47.90, 10.30),
    '88': (47.70, 9.60),
    '89': (48.40, 9.90),
    # 9xxxx - Bayern (Nord)
    '90': (49.45, 11.08),  # Nürnberg
    '91': (49.50, 11.00),
    '92': (49.30, 11.50),
    '93': (49.00, 12.00),
    '94': (48.80, 13.00),
    '95': (49.90, 11.00),
    '96': (49.90, 11.50),
    '97': (50.00, 10.20),
    '98': (50.70, 10.60),
    '99': (51.00, 10.80),
}

# Zusätzliche spezifische PLZ-Koordinaten für häufigere Orte
PLZ_SPECIFIC = {
    '33129': (51.75, 8.37),   # Delbrück
    '33106': (51.65, 8.75),   # Paderborn
    '33100': (51.72, 8.75),   # Paderborn
    '33102': (51.72, 8.75),
    '33104': (51.72, 8.75),
    '33154': (51.62, 8.70),   # Salzkotten
    '33161': (51.55, 8.60),   # Geseke
    '33165': (51.55, 8.80),   # Lichtenau
    '33175': (51.70, 8.55),   # Bad Lippspringe
    '33178': (51.70, 8.62),   # Borchen
    '33181': (51.65, 8.55),   # Bad Wünnenberg
    '33184': (51.50, 8.62),   # Büren
    '33189': (51.80, 8.80),   # Schlangen
    '33330': (51.88, 8.50),   # Gütersloh
    '33332': (51.88, 8.50),
    '33334': (51.88, 8.50),
    '33335': (51.88, 8.50),
    '33378': (51.85, 8.28),   # Rheda-Wiedenbrück
    '33397': (51.80, 8.40),   # Rietberg
    '33415': (51.88, 8.35),   # Verl
    '33428': (51.95, 8.30),   # Harsewinkel
    '33442': (51.78, 8.25),   # Herzebrock-Clarholz
    '33449': (51.80, 8.28),   # Langenberg
    '33600': (52.00, 8.55),   # Bielefeld
    '33602': (52.02, 8.53),
    '33604': (52.02, 8.53),
    '33605': (52.02, 8.53),
    '33607': (52.02, 8.53),
    '33609': (52.02, 8.53),
    '33611': (52.02, 8.53),
    '33613': (52.02, 8.53),
    '33615': (52.02, 8.53),
    '33617': (52.02, 8.53),
    '33619': (52.02, 8.53),
    '33647': (52.00, 8.55),
    '33649': (52.00, 8.55),
    '33659': (52.00, 8.55),
    '33689': (52.00, 8.55),
    '33699': (52.00, 8.55),
    '33729': (52.00, 8.55),
    '33739': (52.00, 8.55),
    '33758': (52.00, 8.55),
    '33775': (52.00, 8.55),
    '33790': (52.00, 8.55),
    '33803': (52.00, 8.55),
    '33813': (52.00, 8.55),
    '33818': (52.00, 8.55),
    '33824': (52.00, 8.55),
    '33829': (52.00, 8.55),
    # Großstädte
    '10115': (52.53, 13.39),  # Berlin Mitte
    '20095': (53.55, 9.99),   # Hamburg
    '80331': (48.14, 11.58),  # München
    '50667': (50.94, 6.96),   # Köln
    '60311': (50.12, 8.68),   # Frankfurt
    '70173': (48.78, 9.18),   # Stuttgart
    '40210': (51.23, 6.78),   # Düsseldorf
    '44135': (51.15, 7.00),   # Dortmund
    '45127': (51.45, 7.00),   # Essen
    '42103': (51.20, 7.10),   # Wuppertal
    '90402': (49.45, 11.08),  # Nürnberg
    '30159': (52.37, 9.74),   # Hannover
    '24103': (54.30, 10.10),  # Kiel
    '18055': (54.09, 12.14),  # Rostock
    '39104': (52.13, 11.62),  # Magdeburg
    '04275': (51.33, 12.37),  # Leipzig
    '01067': (51.05, 13.74),  # Dresden
    '28195': (53.08, 8.80),   # Bremen
    '55116': (50.00, 8.20),   # Mainz
    '99084': (50.98, 11.03),  # Erfurt
    '14467': (52.39, 13.06),  # Potsdam
    '97070': (49.80, 9.94),   # Würzburg
    '68159': (49.49, 8.46),   # Mannheim
    '69115': (49.38, 8.68),   # Heidelberg
    '76133': (49.01, 8.40),   # Karlsruhe
    '79098': (47.99, 7.85),   # Freiburg
    '72070': (48.52, 9.06),   # Tübingen
    '89073': (48.40, 9.98),   # Ulm
    '86150': (48.37, 10.89),  # Augsburg
    '93047': (49.00, 12.09),  # Regensburg
    '44787': (51.50, 7.20),   # Bochum
    '46045': (51.50, 6.90),   # Oberhausen
    '47051': (51.45, 6.75),   # Duisburg
    '41061': (51.20, 6.40),   # Mönchengladbach
    '52062': (50.78, 6.10),   # Aachen
    '53111': (50.73, 7.10),   # Bonn
    '54290': (49.75, 6.64),   # Trier
    '54292': (49.76, 6.67),
    '54294': (49.74, 6.61),
    '54295': (49.77, 6.65),
    '54296': (49.73, 6.69),
    '56068': (50.36, 7.60),   # Koblenz
    '67655': (49.44, 7.77),   # Kaiserslautern
    '66111': (49.23, 7.00),   # Saarbrücken
    '09111': (50.83, 12.92),  # Chemnitz
    '07743': (50.93, 11.58),  # Jena
    '06108': (51.48, 11.97),  # Halle
    '38100': (52.27, 10.53),  # Braunschweig
    '38440': (52.45, 13.30),  # Wolfsburg (circa)
    '29221': (52.65, 10.22),  # Celle
    '21335': (53.23, 10.40),  # Lüneburg
    '49808': (52.50, 7.25),   # Lingen
    '49074': (52.27, 8.05),   # Osnabrück
    '48143': (51.96, 7.63),   # Münster
    '26121': (53.14, 8.20),   # Oldenburg
    '26382': (53.54, 8.00),   # Wilhelmshaven
    '27568': (53.55, 8.60),   # Bremerhaven
    '30449': (52.38, 9.74),   # Hannover (weiter)
    '24937': (54.78, 9.44),   # Flensburg
    '23539': (53.87, 10.69),  # Lübeck
    '19053': (53.37, 11.42),  # Schwerin
    '14469': (52.41, 13.02),  # Potsdam
    '15738': (52.30, 13.55),  # Königs Wusterhausen
    '15230': (52.28, 14.50),  # Frankfurt (Oder)
    '03046': (51.75, 14.33),  # Cottbus
    '02625': (51.17, 14.43),  # Bautzen
    '08056': (50.72, 12.50),  # Zwickau
    '98527': (50.68, 10.91),  # Suhl
    '96450': (50.28, 10.95),  # Coburg
    '87435': (47.60, 10.20),  # Kempten
    '88131': (47.55, 9.70),   # Lindau
    '78224': (47.70, 8.85),   # Singen
    '78462': (47.66, 9.17),   # Konstanz
    '78048': (48.10, 8.30),   # Villingen-Schwenningen
    '73728': (48.70, 9.50),   # Esslingen
    '72764': (48.50, 9.20),   # Reutlingen
    '89518': (48.66, 10.10),  # Heidenheim
    '91550': (49.13, 10.07),  # Dinkelsbühl
    '91560': (49.25, 10.30),  # Feuchtwangen
    '91575': (49.23, 10.20),  # Wörnitz
    '91580': (49.25, 10.20),  # Petersaurach
    '91583': (49.25, 10.05),  # Schillingsfürst
    '91586': (49.16, 10.33),  # Lichtenau
    '91587': (49.25, 10.00),  # Adelshofen
    '91589': (49.20, 10.15),  # Aurach
    '91590': (49.20, 10.10),  # Gebsattel
    '91592': (49.20, 10.25),  # Buch am Wald
    '91593': (49.30, 10.10),  # Burgbernheim
    '91595': (49.30, 10.20),  # Marktbergel
    '91596': (49.22, 10.14),  # Burk
    '91598': (49.28, 10.12),  # Colmberg
    '91599': (49.10, 10.20),  # Dentlein
    '91710': (49.10, 10.50),  # Gunzenhausen
    '91717': (49.03, 10.60),  # Wassertrüdingen
    '91720': (49.15, 10.60),  # Heidenheim
    '91723': (49.05, 10.70),  # Dittenheim
    '91725': (49.07, 10.59),  # Ehingen
    '91726': (49.14, 10.54),  # Gerolfingen
    '91728': (49.14, 10.64),  # Gnotzheim
    '91729': (49.10, 10.65),  # Haundorf
    '91731': (49.10, 10.55),  # Langfurth
    '91732': (49.12, 10.60),  # Merkendorf
    '91734': (49.10, 10.70),  # Mitteleschenbach
    '91735': (49.07, 10.68),  # Muhr am See
    '91737': (49.05, 10.53),  # Ornbau
    '91738': (49.10, 10.60),  # Pfofeld
    '91740': (49.02, 10.57),  # Röckingen
    '91741': (49.12, 10.69),  # Theilenhofen
    '91743': (49.13, 10.60),  # Unterschwaningen
    '91744': (49.05, 10.74),  # Weiltingen
    '91746': (49.08, 10.65),  # Weidenbach
    '91747': (49.09, 10.58),  # Westheim
    '91749': (49.04, 10.62),  # Wittelshofen
    '91757': (49.00, 10.80),  # Treuchtlingen
    '91781': (49.02, 10.90),  # Weißenburg
    '91785': (48.97, 10.85),  # Pleinfeld
    '91788': (49.00, 10.95),  # Pappenheim
    '91790': (49.05, 10.95),  # Nennslingen
    '91792': (49.10, 10.90),  # Bergen
    '91793': (49.07, 10.90),  # Alesheim
    '91795': (49.00, 10.86),  # Ettenstatt
    '91796': (49.05, 10.80),  # Höttingen
    '91798': (49.10, 10.80),  # Hörlbach
    '91799': (49.02, 10.90),  # Langenaltheim
    '91802': (49.04, 10.87),  # Meinheim
    '91804': (49.08, 10.87),  # Mönchsroth
    '91805': (49.01, 10.98),  # Treuchtlingen
    '91807': (49.03, 10.83),  # Markt Berolzheim
}


# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def log(msg):
    """Einheitliche Log-Ausgabe mit Zeitstempel."""
    ts = time.strftime('%H:%M:%S')
    print(f'[{ts}] {msg}')
    sys.stdout.flush()


def get_plz_coords(plz):
    """
    Gibt (lat, lon) für eine 5-stellige PLZ zurück.
    Zuerst spezifische PLZ prüfen, dann auf Bereichsebene (2-stellig) fallen.
    """
    plz_str = str(plz).strip()
    if plz_str in PLZ_SPECIFIC:
        return PLZ_SPECIFIC[plz_str]
    prefix = plz_str[:2] if len(plz_str) >= 2 else plz_str
    if prefix in PLZ_COORDS:
        return PLZ_COORDS[prefix]
    # Fallback: Berlin Mitte
    log(f'  ⚠ Keine Koordinaten für PLZ {plz_str}, verwende Fallback (Berlin)')
    return (52.52, 13.41)


def haversine(lat1, lon1, lat2, lon2):
    """
    Berechnet die Entfernung in km zwischen zwei GPS-Koordinaten
    mittels Haversine-Formel.
    """
    R = 6371  # Erdradius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)


def extract_plz_from_text(text):
    """Extrahiert eine 5-stellige deutsche PLZ aus einem Text."""
    if not text:
        return None
    matches = re.findall(r'\b(\d{5})\b', text)
    for m in matches:
        if 1000 <= int(m) <= 99999:
            return m
    return None


def parse_price(price_text):
    """Parst einen Preis aus Text, gibt float oder None zurück."""
    if not price_text:
        return None
    price_text = price_text.replace('.', '').replace(',', '.')
    match = re.search(r'(\d+(?:\.\d{1,2})?)', price_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


# ─── Notion API ──────────────────────────────────────────────────────────────

def load_token():
    """Lädt den Notion-API-Token aus der Datei."""
    try:
        with open('C:/Users/renko/notion_key_test.txt') as f:
            token = f.read().strip()
        if not token:
            log('❌ Kein Token in notion_key_test.txt gefunden')
            sys.exit(1)
        log(f'🔑 Token geladen: {token[:10]}...{token[-4:]} ({len(token)} Zeichen)')
        return token
    except FileNotFoundError:
        log('❌ Datei notion_key_test.txt nicht gefunden')
        sys.exit(1)


def notion_api(endpoint, data=None, method='POST', token=None):
    """Führt einen Notion-API-Aufruf aus."""
    if token is None:
        token = TOKEN
    url = f'{BASE_URL}/{endpoint}'
    payload = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=payload, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Notion-Version', NOTION_VERSION)
    if payload:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode('utf-8')
            parsed = json.loads(raw)
            ok = parsed.get('object') != 'error'
            if not ok:
                log(f'  ❌ Notion API Error ({endpoint}): {parsed.get("message","?")}')
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            parsed = json.loads(body)
            msg = parsed.get('message', body[:200])
        except json.JSONDecodeError:
            msg = body[:200]
        log(f'  ❌ Notion HTTP {e.code} ({endpoint}): {msg}')
        return e.code, json.loads(body) if body else {}
    except Exception as e:
        log(f'  ❌ Notion Exception ({endpoint}): {e}')
        return 0, {}


def query_database(db_id, filter_data=None, token=None):
    """Alle Einträge aus einer Notion-Datenbank abfragen (mit Paginierung)."""
    all_results = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {'page_size': PAGE_SIZE}
        if filter_data:
            payload['filter'] = filter_data
        if next_cursor:
            payload['start_cursor'] = next_cursor

        status, data = notion_api(f'databases/{db_id}/query', payload,
                                  token=token)
        if status >= 400 or data.get('object') == 'error':
            log(f'  ❌ Fehler beim Abfragen der DB: {data.get("message","?")}')
            return []

        results = data.get('results', [])
        all_results.extend(results)
        has_more = data.get('has_more', False)
        next_cursor = data.get('next_cursor')

    return all_results


def extract_property_value(properties, prop_name):
    """Extrahiert den Wert einer Notion-Property anhand ihres Namens."""
    prop = properties.get(prop_name, {})
    ptype = prop.get('type', '?')

    if ptype == 'title':
        texts = prop.get('title', [])
        return ''.join(t.get('plain_text', '') for t in texts)
    elif ptype == 'rich_text':
        texts = prop.get('rich_text', [])
        return ''.join(t.get('plain_text', '') for t in texts)
    elif ptype == 'number':
        return prop.get('number')
    elif ptype == 'url':
        return prop.get('url', '')
    elif ptype == 'select':
        s = prop.get('select')
        return s['name'] if s else None
    elif ptype == 'multi_select':
        items = [s['name'] for s in prop.get('multi_select', [])]
        return items
    elif ptype == 'status':
        s = prop.get('status')
        return s['name'] if s else None
    elif ptype == 'date':
        d = prop.get('date')
        return d['start'] if d else None
    elif ptype == 'checkbox':
        return prop.get('checkbox', False)
    else:
        return prop.get(ptype, None)


def create_page(database_id, properties, token=None):
    """Erstellt eine neue Seite in einer Notion-Datenbank."""
    data = {
        'parent': {'database_id': database_id},
        'properties': properties,
    }
    status, resp = notion_api('pages', data, token=token)
    if status in (200, 201):
        return resp
    else:
        log(f'  ❌ Fehler beim Erstellen der Seite: {resp.get("message","?")}')
        return None


# ─── Kleinanzeigen Scraper ──────────────────────────────────────────────────

def fetch_kleinanzeigen(search_term, max_price, plz, radius):
    """
    Ruft die Kleinanzeigen-Suche mit Standort- und Radius-Filter auf.
    Gibt eine Liste von gefundenen Artikeln zurück.
    """
    # Suchbegriff URL-encoden: Leerzeichen → -
    search_enc = search_term.strip().lower().replace(' ', '-')
    search_enc = re.sub(r'[^a-z0-9\-]', '', search_enc)

    if plz and radius:
        # Kleinanzeigen ignoriert l{plz}r{radius} im Pfad (liefert ungefilterte
        # Ergebnisse aus ganz Deutschland). Stattdessen das Suchformular mit
        # GET-Parametern verwenden – Kleinanzeigen leitet dann auf die korrekte
        # URL (mit interner locationId) weiter.
        url = (f'{KA_BASE}/s-suchanfrage.html?keywords={search_enc}'
               f'&locationStr={plz}&radius={radius}')
    else:
        url = f'{KA_BASE}/s-{search_enc}/k0'

    # maxPrice nur anhängen, wenn gesetzt
    if max_price and str(max_price).strip():
        sep = '&' if '?' in url else '?'
        url += f'{sep}maxPrice={max_price}'

    log(f'  🌐 URL: {url}')

    # Zufällige Verzögerung vor dem Request (Rate-Limit / IP-Block vermeiden)
    delay = random.uniform(2.0, 5.0)
    log(f'  ⏳ Warte {delay:.1f}s vor dem Request...')
    time.sleep(delay)

    # User-Agent zufällig wählen
    ua = random.choice(USER_AGENTS)

    # Headers wie ein echter Browser
    headers = {
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.kleinanzeigen.de/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
    }

    articles = []

    if HAS_REQUESTS:
        try:
            session = requests.Session()
            session.headers.update(headers)
            resp = session.get(url, timeout=30)
            resp.encoding = 'utf-8'
            html = resp.text

            if resp.status_code == 403:
                log(f'  ⛔ Kleinanzeigen blockiert die Anfrage (403). IP-Bereich vorübergehend gesperrt.')
                log(f'  ⛔ Bitte später erneut versuchen oder VPN/Proxy verwenden.')
                return []
            if resp.status_code != 200:
                log(f'  ❌ HTTP {resp.status_code}: {resp.reason}')
                return []
        except Exception as e:
            log(f'  ❌ Fehler beim Abrufen (requests): {e}')
            return []
    else:
        # Fallback: urllib
        req = urllib.request.Request(url)
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 403:
                log(f'  ⛔ Kleinanzeigen blockiert die Anfrage (403). IP-Bereich vorübergehend gesperrt.')
                log(f'  ⛔ Bitte später erneut versuchen oder VPN/Proxy verwenden.')
            else:
                log(f'  ❌ HTTP {e.code} beim Abrufen (urllib): {e.reason}')
            return []
        except Exception as e:
            log(f'  ❌ Fehler beim Abrufen (urllib): {e}')
            return []

    # ─── Artikel parsen ───
    # Methode 1: JSON-LD ItemList (strukturierteste Daten)
    jsonld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    jsonld_matches = re.findall(jsonld_pattern, html, re.DOTALL)

    item_list = None
    for j in jsonld_matches:
        try:
            data = json.loads(j)
            if isinstance(data, dict) and data.get('@type') == 'ItemList':
                item_list = data
                break
        except json.JSONDecodeError:
            continue

    if item_list and 'itemListElement' in item_list:
        log('  📦 JSON-LD ItemList gefunden')
        for element in item_list['itemListElement']:
            item = element if isinstance(element, dict) else {}
            # item kann direkt das Product sein oder in 'item' verschachtelt
            product = item.get('item', item)
            if isinstance(product, dict):
                articles.append(product)
    else:
        log('  📄 Keine ItemList-JSONLD, Artikel aus JSON-LD in <article> extrahieren')

    # Methode 2: <article class="aditem"> mit JSON-LD darin parsen
    if len(articles) < 5:
        log('  🔍 Parst <article> Elemente...')
        article_matches = re.finditer(
            r'<article[^>]*class="[^"]*aditem[^"]*"[^>]*>(.*?)</article>',
            html, re.DOTALL
        )

        for m in article_matches:
            article_tag = m.group(0)               # voller <article...>...</article>
            article_html = m.group(1)               # Inhalt zwischen den Tags
            article = {}

            # data-href extrahieren – steht AUF dem <article>-Tag, nicht im Content
            data_href = re.search(r'data-href="(/s-anzeige/[^"]+)"', article_tag)
            if data_href:
                article['url'] = KA_BASE + data_href.group(1)
            else:
                # Fallback: href im Content (z.B. <a href="...">)
                link_match = re.search(r'href="(/s-anzeige/[^"]+)"', article_html)
                if link_match:
                    article['url'] = KA_BASE + link_match.group(1)

            # JSON-LD im Article-Scope
            jld_in_article = re.search(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                                       article_html, re.DOTALL)
            if jld_in_article:
                try:
                    jld_data = json.loads(jld_in_article.group(1))
                    if isinstance(jld_data, dict):
                        article['_jsonld'] = jld_data
                        article['name'] = jld_data.get('title') or jld_data.get('name', '')
                        if not article.get('url'):
                            url_jld = jld_data.get('url', '')
                            if url_jld:
                                article['url'] = url_jld if url_jld.startswith('http') else KA_BASE + url_jld
                        offers = jld_data.get('offers', {})
                        if isinstance(offers, dict):
                            price = offers.get('price')
                            if price is not None:
                                try:
                                    article['price'] = float(price)
                                except (ValueError, TypeError):
                                    pass
                except json.JSONDecodeError:
                    pass

            # Titel aus HTML (falls nicht aus JSON-LD)
            if 'name' not in article or not article.get('name'):
                title_match = re.search(
                    r'<a[^>]*class="[^"]*ellipsis[^"]*"[^>]*>\s*([^<]+?)\s*</a>',
                    article_html, re.DOTALL
                )
                if title_match:
                    article['name'] = title_match.group(1).strip()
                else:
                    title_match = re.search(r'alt="([^"]*)"', article_html)
                    if title_match:
                        article['name'] = title_match.group(1).strip()

            # Preis aus HTML (falls nicht aus JSON-LD)
            if 'price' not in article:
                price_match = re.search(
                    r'<([a-z]+)[^>]*class="[^"]*aditem-main--middle--price-shipping--price[^"]*"[^>]*>\s*(\d+[\.\,]?\d*)\s*€',
                    article_html
                )
                if price_match:
                    article['price'] = parse_price(price_match.group(2))

            # Ort/PLZ
            location_match = re.search(
                r'<div[^>]*class="[^"]*aditem-main--top--left[^"]*"[^>]*>(.*?)</div>',
                article_html, re.DOTALL
            )
            if location_match:
                loc_html = location_match.group(1)
                loc_text = re.sub(r'<[^>]+>', ' ', loc_html).strip()
                loc_text = re.sub(r'\s+', ' ', loc_text)
                article['location'] = loc_text
                # Kleinanzeigen-eigene Distanz aus dem Location-Text extrahieren
                # Formate: "(14 km)", "(0.0 km)", "(ca. 25 km)"
                dist_match = re.search(
                    r'\((?:(?:ca\.?)\s*)?(\d+(?:[.,]\d+)?)\s*km\)',
                    loc_text, re.IGNORECASE
                )
                if dist_match:
                    ka_dist = dist_match.group(1).replace(',', '.')
                    try:
                        article['ka_distance'] = float(ka_dist)
                    except ValueError:
                        pass

            if article.get('name') or article.get('url'):
                articles.append(article)

    # Deduplizieren nach URL
    seen_urls = set()
    unique_articles = []
    for a in articles:
        url = a.get('url', '').strip().rstrip('/')
        name = a.get('name', '').strip()

        if not name and not url:
            continue
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)

        # PLZ aus location extrahieren
        loc_text = a.get('location', '')
        plz_found = extract_plz_from_text(loc_text)
        if not plz_found:
            # Versuche aus JSON-LD
            jld = a.get('_jsonld', {})
            if isinstance(jld, dict):
                addr = jld.get('offers', {}).get('seller', {}).get('address', {}) if isinstance(jld.get('offers'), dict) else {}
                if not isinstance(addr, dict):
                    addr = {}
                plz_found = addr.get('postalCode', '')
                if not plz_found:
                    loc_from_addr = ' '.join(filter(None, [
                        addr.get('postalCode', ''),
                        addr.get('addressLocality', ''),
                    ]))
                    if loc_from_addr:
                        a['location'] = loc_from_addr
                        plz_found = extract_plz_from_text(loc_from_addr)

        a['location_plz'] = plz_found or None

        # Name bereinigen
        a['name'] = name or '(kein Titel)'
        a['price'] = a.get('price')

        # JSON-LD-Rohdaten entfernen (nicht für Ausgabe benötigt)
        a.pop('_jsonld', None)

        unique_articles.append(a)

    # Preise normalisieren
    for a in unique_articles:
        if a.get('price') is None:
            a['price'] = None

    log(f'  📊 {len(unique_articles)} unique Artikel gefunden')
    return unique_articles


def filter_by_distance(articles, search_plz, max_radius_km):
    """
    Filtert Artikel nach maximaler Entfernung (Luftlinie) zur Such-PLZ.
    Berechnet die Entfernung für jeden Artikel.
    Gibt Artikel mit berechneter Entfernung zurück.
    """
    if not search_plz or not max_radius_km:
        return articles

    search_coords = get_plz_coords(search_plz)
    filtered = []

    for a in articles:
        # Kleinanzeigen-eigene Distanz bevorzugen (genauer als Haversine
        # mit groben PLZ-Koordinaten)
        ka_dist = a.get('ka_distance')
        if ka_dist is not None:
            a['distance'] = ka_dist
            if ka_dist <= max_radius_km:
                filtered.append(a)
            else:
                a['_skipped_reason'] = f'Entfernung {ka_dist}km > {max_radius_km}km (KA-Angabe)'
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
                a['_skipped_reason'] = f'Entfernung {distance}km > {max_radius_km}km'
        else:
            # Keine PLZ gefunden → Artikel trotzdem aufnehmen, Entfernung auf -1
            a['distance'] = -1
            a['_skipped_reason'] = 'Keine PLZ im Artikel gefunden'
            # Wir lassen ihn trotzdem durch, markieren ihn aber
            filtered.append(a)

    return filtered


# ─── Dubletten-Prüfung ──────────────────────────────────────────────────────

def get_existing_links(db_id, token=None):
    """
    Holt alle vorhandenen Ergebnis-Links aus der Ergebnis-DB.
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


# ─── Hauptlogik ──────────────────────────────────────────────────────────────

def main():
    log('═' * 60)
    log('🔍 KLEINANZEIGEN SEARCH — Automatisierte Suche')
    log('═' * 60)

    # Token laden
    TOKEN = load_token()
    log(f'  Token OK: {TOKEN[:10]}...{TOKEN[-4:]}')

    # ─── Schritt 1: Suchparameter aus DB1 lesen ───
    log('')
    log('📖 Schritt 1: Lese Suchparameter aus DB "Artikel"...')
    search_entries = query_database(DB_SEARCH_ID, token=TOKEN)
    log(f'  ✅ {len(search_entries)} Suchanfragen gefunden')

    if not search_entries:
        log('❌ Keine Suchanfragen in der Datenbank.')
        sys.exit(0)

    # ─── Schritt 2: Vorhandene Links aus DB2 laden ───
    log('')
    log('📖 Schritt 2: Lade vorhandene Ergebnisse aus DB "Gefunden Artikel"...')
    existing_links = get_existing_links(DB_RESULT_ID, token=TOKEN)

    # ─── Schritt 3: Für jede Suchanfrage ausführen ───
    total_new = 0
    total_skipped = 0
    total_errors = 0

    for idx, entry in enumerate(search_entries):
        props = entry.get('properties', {})
        entry_id = entry.get('id', '?')
        created = entry.get('created_time', '?')

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
            articles = fetch_kleinanzeigen(artikelname, int(max_price) if max_price < 999999 else '', plz, int(radius_km) if radius_km else None)
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
            articles_filtered = [a for a in articles if '_skipped_reason' not in a or 'Entfernung' not in a.get('_skipped_reason', '')]
            removed_count = before - len(articles_filtered)
            if removed_count > 0:
                log(f'  🗑 {removed_count} Artikel wegen Entfernung >{radius_km}km entfernt')
                for a in articles:
                    if '_skipped_reason' in a and 'Entfernung' in a['_skipped_reason']:
                        log(f'    ↳ {a.get("name","?")} — {a["_skipped_reason"]}')
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
                location = a.get('location', '')[:30] if a.get('location') else ''
                distance = a.get('distance', -1)
                link = a.get('url', '')

                # Notion-Properties
                properties = {
                    'Artikelname': {
                        'title': [{'text': {'content': name}}]
                    },
                    'Preis': {
                        'number': price_val if price_val is not None else None
                    },
                    'Ort': {
                        'rich_text': [{'text': {'content': location}}]
                    },
                    'Entfernung': {
                        'number': distance if distance >= 0 else None
                    },
                    'Link': {
                        'url': link if link else None
                    },
                    'Gefunden am': {
                        'date': {'start': datetime.datetime.now().isoformat()}
                    },
                }

                result = create_page(DB_RESULT_ID, properties, token=TOKEN)
                if result:
                    total_new += 1
                    dist_str = f', {distance}km' if distance >= 0 else ''
                    log(f'  ✅ [{i+1}/{len(new_articles)}] {name} — {price_val}€ — {location}{dist_str}')
                    existing_links.add(link)  # Für spätere Dubletten-Prüfung
                else:
                    total_errors += 1

            # Kurze Pause zwischen Artikeln (Rate-Limit vermeiden)
            time.sleep(random.uniform(1.5, 3.0))
        else:
            log('  💤 Nichts Neues für diese Suchanfrage')

        # Kurze Pause zwischen Suchanfragen (Rate-Limit vermeiden)
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


if __name__ == '__main__':
    main()
