"""Geo-Funktionen: PLZ-Extraktion und Preis-Parsing.

Enthält Hilfsfunktionen zum Extrahieren von PLZ aus Text
und zum Parsen von Preisen. KEINE Koordinaten-Datenbank mehr —
Kleinanzeigen liefert Distanzen direkt serverseitig.
"""

import re


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
