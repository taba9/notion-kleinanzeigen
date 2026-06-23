# Notion-Kleinanzeigen

Automatisierte Kleinanzeigen-Suche mit Notion-Datenbank-Anbindung.

## Funktion

1. Liest Suchparameter (Artikelname, Max-Preis, Ort, Umkreis) aus einer **Notion-Datenbank**
2. Sucht automatisch auf **Kleinanzeigen** nach passenden Artikeln
3. Filtert nach **Entfernung** und **Preis**
4. Schreibt gefundene Artikel in eine zweite **Notion-Datenbank** (mit Link, Preis, Ort, Entfernung, Timestamp)

## Setup

### 1. Notion-Integration
1. Gehe zu https://www.notion.so/profile/integrations
2. Erstelle eine interne Integration → kopiere den API-Key
3. Speichere den Key in `notion_key.txt` (wird von `.gitignore` ausgeschlossen)

### 2. Notion-Datenbanken

**Such-DB „Artikel"** (ID: `d2901790-6cd9-4c9f-b949-7c93e6987be7`):
- `Artikelname` (Titel)
- `Preis` (Zahl)
- `Ort` (Text) — PLZ oder Ort
- `Umkreis` (Zahl) — in km

**Ergebnis-DB „Gefunden Artikel"** (ID: `388231b1-2b4e-806d-b628-f542c39c2f19`):
- `Artikelname` (Titel)
- `Preis` (Zahl)
- `Ort` (Text)
- `Entfernung` (Zahl) — in km
- `Link` (URL)
- `Gefunden am` (Datum)

### 3. Ausführen

```bash
python kleinanzeigen_search.py
```

Der API-Key wird automatisch aus `notion_key.txt` geladen.

## Technisches

- Python 3.11+ (kein `requests` nötig — nur Stdlib)
- Notion API Version `2022-06-28`
- Kleinanzeigen-Suche via Formular-Parameter (`locationStr` + `radius`)
- Entfernungsfilter nutzt Kleinanzeigens eigene Distanzangabe (Fallback: Haversine)
- User-Agent Rotation und zufällige Verzögerungen zur Vermeidung von IP-Blocks
