#!/usr/bin/env python
"""Entrypoint: Führt die Kleinanzeigen-Suche mit Notion-Anbindung aus.

Usage:
    python scripts/run_search.py          # Normale Ausführung
    python scripts/run_search.py --dry-run  # Nur Simulation, keine DB-Schreibvorgänge
"""

import sys
import os

# Projekt-Root zum Python-Pfad hinzufügen, damit `from src.xxx` funktioniert
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.workflow import run


def main():
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    run(dry_run=dry_run)


if __name__ == '__main__':
    main()
