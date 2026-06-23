"""Filter-Logik für Kleinanzeigen-Artikel.

Enthält Preis-Filter und Dubletten-Prüfung — ausgelagert aus dem
Workflow, damit die Logik isoliert testbar und wiederverwendbar ist.
"""

from .logger import log


def filter_by_price(articles, max_price):
    """Filtert Artikel, die über dem Maximalpreis liegen.

    Args:
        articles: Liste von Artikel-Dicts
        max_price: Maximaler Preis (float). 999999 = deaktiviert.

    Returns:
        Tuple (gefilterte_artikel, anzahl_übersprungen)
    """
    if max_price >= 999999:
        return articles, 0

    filtered = []
    skipped = 0
    for a in articles:
        price = a.get('price')
        if price is not None and price > max_price:
            skipped += 1
            continue
        filtered.append(a)

    return filtered, skipped


def deduplicate_by_url(articles, existing_links):
    """Entfernt Artikel, deren URL bereits in der Ergebnis-DB existiert.

    Args:
        articles: Liste von Artikel-Dicts
        existing_links: Set von existierenden URLs

    Returns:
        Tuple (neue_artikel, anzahl_übersprungen)
    """
    new_articles = []
    skipped = 0
    for a in articles:
        url = a.get('url', '').strip().rstrip('/')
        if url and url in existing_links:
            skipped += 1
            continue
        new_articles.append(a)

    return new_articles, skipped


def apply_all_filters(articles, max_price, existing_links):
    """Wendet alle Filter in der richtigen Reihenfolge an.

    Reihenfolge:
    1. Preis-Filter (günstigere Filter zuerst)
    2. Dubletten-Check (teurer, da API-Call pro Prüfung)

    Args:
        articles: Liste von Artikel-Dicts
        max_price: Maximaler Preis
        existing_links: Set von existierenden URLs

    Returns:
        Tuple (gefilterte_artikel, stats_dict)
    """
    stats = {'price_skipped': 0, 'duplicate_skipped': 0}

    # 1. Preis
    articles, price_skipped = filter_by_price(articles, max_price)
    stats['price_skipped'] = price_skipped

    # 2. Dubletten
    articles, dup_skipped = deduplicate_by_url(articles, existing_links)
    stats['duplicate_skipped'] = dup_skipped

    return articles, stats
