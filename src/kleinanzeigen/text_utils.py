"""Text-Hilfsfunktionen: PLZ-Extraktion und Preis-Parsing.

Enthält reine Textverarbeitungs-Funktionen, die sowohl von
der Kleinanzeigen-Suche als auch vom Workflow genutzt werden.
KEINE Geo-Koordinaten oder Distanzberechnungen mehr —
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
    """Parst einen Preis aus Text, gibt float oder None zurück.

    Heuristik für Tausender-Trenner:
    - Wenn Punkt UND Komma vorkommen → Punkt ist Tausender, Komma ist Dezimal
    - Wenn nur Komma vorkommt → Komma ist Dezimal (deutsches Format)
    - Wenn nur Punkt vorkommt → Punkt ist Dezimal (internationales Format)
    """
    if not price_text:
        return None

    # Heuristik für Tausender-Trenner
    if '.' in price_text and ',' in price_text:
        # Punkt = Tausender, Komma = Dezimal (z.B. "1.234,56 €")
        price_text = price_text.replace('.', '').replace(',', '.')
    elif ',' in price_text:
        # Nur Komma = deutsches Dezimal-Trennzeichen (z.B. "12,99 €")
        price_text = price_text.replace(',', '.')
    # else: Nur Punkt = internationales Dezimal-Trennzeichen (z.B. "12.99 €")
    # → nichts tun

    match = re.search(r'(\d+(?:\.\d{1,2})?)', price_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None
