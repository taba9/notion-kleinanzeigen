# Notion-Kleinanzeigen

Automatisierte Kleinanzeigen-Suche mit Notion-Datenbank-Anbindung.

## Funktion

1. Liest Suchparameter (Artikelname, Max-Preis, Ort, Umkreis) aus einer **Notion-Datenbank**
2. Sucht automatisch auf **Kleinanzeigen** nach passenden Artikeln
3. Filtert nach **Entfernung** und **Preis**
4. Schreibt gefundene Artikel in eine zweite **Notion-Datenbank** (mit Link, Preis, Ort, Entfernung, Timestamp)

## Projektstruktur

```
notion-kleinanzeigen/
├── README.md
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── config.py              # Token-Laden, DB-IDs, Konstanten
│   ├── logger.py              # 🆕 Einheitliches Logging
│   ├── filters.py             # 🆕 Preis- + Dubletten-Filter
│   ├── workflow.py            # Orchestrierung (verbindet Notion + KA)
│   ├── notion/
│   │   ├── __init__.py
│   │   ├── client.py          # Notion-API-Wrapper (nur urllib)
│   │   └── properties.py      # 🆕 Schema-Property-Builder für DBs
│   └── kleinanzeigen/
│       ├── __init__.py
│       ├── search.py          # URL-Bau, HTML-Parsing, Extraktion
│       ├── text_utils.py      # 🆕 Text-Helfer (PLZ, Preis u.a.)
│       └── user_agents.py     # User-Agent-Rotation
└── scripts/
    ├── run_search.py          # Entrypoint (--dry-run, --force)
    └── inspect_db.py          # DB-Inspektion (Schema + Einträge)
```

## Setup

### 1. Notion-Integration

1. Gehe zu https://www.notion.so/profile/integrations
2. Erstelle eine interne Integration → kopiere den API-Key
3. Speichere den Key in `C:\Users\renko\notion_key_test.txt` (wird von `.gitignore` ausgeschlossen)

Oder setze die Umgebungsvariable `NOTION_TOKEN_PATH` auf einen anderen Pfad.

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
# Normale Suche (schreibt Ergebnisse in Notion)
python scripts/run_search.py

# Dry Run (nur Simulation, keine Schreibvorgänge)
python scripts/run_search.py --dry-run

# Datenbanken inspizieren
python scripts/inspect_db.py
```

**Wichtig:** Immer aus dem Projekt-Root-Verzeichnis ausführen.

## Technisches

- **Python 3.11+** (kein `requests` nötig — nur Stdlib `urllib`)
- **Notion API Version `2022-06-28`** — `2025-09-03` liefert `invalid_request_url` für Linked Databases
- **Kleinanzeigen-Suche** via Formular-Parameter (`locationStr` + `radius`)
- **Entfernungsfilter** nutzt Kleinanzeigens eigene Distanzangabe (Fallback: Haversine mit PLZ-Koordinaten)
- **User-Agent Rotation** und zufällige Verzögerungen zur Vermeidung von IP-Blocks
- **Strikte Trennung:** `src/notion/` und `src/kleinanzeigen/` importieren sich gegenseitig nicht

## Hinweise

- Bei IP-Block (HTTP 403) hilft nur warten (Stunden) oder VPN/Proxy verwenden
- Der API-Key muss in `notion_key_test.txt` liegen (Standardpfad) oder via `NOTION_TOKEN_PATH` konfiguriert sein
- Keine externen Dependencies — nur Python Standard Library
