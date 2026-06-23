"""Konfiguration und Token-Laden für Notion-Kleinanzeigen."""

import os

NOTION_VERSION = '2022-06-28'
BASE_URL = 'https://api.notion.com/v1'
PAGE_SIZE = 100

# Datenbanken
DB_SEARCH_ID = 'd2901790-6cd9-4c9f-b949-7c93e6987be7'   # "Artikel" (Suchanfragen)
DB_RESULT_ID = '388231b1-2b4e-806d-b628-f542c39c2f19'    # "Gefunden Artikel" (Ergebnisse)

# Kleinanzeigen Basis-URL
KA_BASE = 'https://www.kleinanzeigen.de'


def load_token():
    """Lädt Notion-API-Token aus Datei.

    Liest den Token aus der in NOTION_TOKEN_PATH oder dem Standardpfad
    hinterlegten Datei. Gibt den Token als String zurück.
    """
    path = os.environ.get('NOTION_TOKEN_PATH', 'C:/Users/renko/notion_key_test.txt')
    with open(path) as f:
        token = f.read().strip()
    if not token:
        raise ValueError(f'Kein Token in {path} gefunden')
    return token
