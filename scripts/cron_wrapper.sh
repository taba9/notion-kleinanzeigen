#!/usr/bin/env bash
# Hermes Cron-Wrapper für notion-kleinanzeigen Suche
# Führt die automatisierte Kleinanzeigen-Suche aus und liefert
# die Zusammenfassung per Telegram.
set -e

PROJECT_DIR="/c/Users/renko/notion-kleinanzeigen"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Projektverzeichnis $PROJECT_DIR nicht gefunden!"
    exit 1
fi

cd "$PROJECT_DIR"
echo "📂 $(date '+%Y-%m-%d %H:%M') — Starte notion-kleinanzeigen Suche"
echo ""
python scripts/run_search.py
