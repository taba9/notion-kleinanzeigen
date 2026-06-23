#!/usr/bin/env python
"""Entrypoint: Führt die Kleinanzeigen-Suche mit Notion-Anbindung aus.

Usage:
    python scripts/run_search.py              # Normale Ausführung
    python scripts/run_search.py --dry-run    # Nur Simulation
    python scripts/run_search.py --force      # Überspringe Zeit-Prüfungen
    python scripts/run_search.py -n           # Kurzform für dry-run

Examples:
    python scripts/run_search.py
    python scripts/run_search.py --dry-run
    python scripts/run_search.py --force
"""

import sys
import os

# Projekt-Root zum Python-Pfad hinzufügen
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.workflow import run


def main():
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    force = '--force' in sys.argv or '-f' in sys.argv

    # Hilfe anzeigen
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        return

    run(dry_run=dry_run, force=force)


if __name__ == '__main__':
    main()
