"""Kleinanzeigen-Suche — URL-Bau und HTML-Parsing.

Enthält die Logik zum Suchen auf Kleinanzeigen und Parsen der Ergebnisse.
Importiert NIEMALS aus src/notion/.
"""

import json
import re
import time
import random
import urllib.request
import urllib.error

from ..config import KA_BASE
from ..logger import log
from .user_agents import random_user_agent
from .text_utils import parse_price, extract_plz_from_text


def build_search_url(search_term, max_price=None, plz=None, radius=None):
    """Baut die Kleinanzeigen-Such-URL mit Parametern.

    Args:
        search_term: Suchbegriff
        max_price: Optionaler Maximalpreis
        plz: Optionale PLZ für Standortfilter
        radius: Optionaler Radius in km

    Returns:
        Vollständige Such-URL
    """
    # Suchbegriff URL-encoden: Leerzeichen → -
    search_enc = search_term.strip().lower().replace(' ', '-')
    search_enc = re.sub(r'[^a-z0-9\-]', '', search_enc)

    if plz and radius:
        url = (f'{KA_BASE}/s-suchanfrage.html?keywords={search_enc}'
               f'&locationStr={plz}&radius={radius}')
    else:
        url = f'{KA_BASE}/s-{search_enc}/k0'

    # maxPrice nur anhängen, wenn gesetzt
    if max_price and str(max_price).strip():
        sep = '&' if '?' in url else '?'
        url += f'{sep}maxPrice={max_price}'

    return url


def _fetch_html(url):
    """Ruft eine URL ab und gibt den HTML-Text zurück.

    Nutzt User-Agent-Rotation und zufällige Verzögerung.
    Gibt bei Fehler (403 etc.) None zurück.
    """
    # Zufällige Verzögerung vor dem Request (Rate-Limit / IP-Block vermeiden)
    delay = random.uniform(2.0, 5.0)
    time.sleep(delay)

    ua = random_user_agent()

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

    req = urllib.request.Request(url)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
        return html
    except urllib.error.HTTPError as e:
        if e.code == 403:
            log(f'  ⚠ HTTP 403 (IP-Block) für {url}', '')
            return None  # IP block
        log(f'  ⚠ HTTP {e.code} für {url}', '')
        return None
    except Exception as e:
        log(f'  ⚠ Fehler beim Abrufen von {url}: {type(e).__name__}: {e}', '')
        return None


def _parse_jsonld(html):
    """Versucht, Artikel aus JSON-LD ItemList zu extrahieren."""
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

    articles = []
    if item_list and 'itemListElement' in item_list:
        for element in item_list['itemListElement']:
            item = element if isinstance(element, dict) else {}
            product = item.get('item', item)
            if isinstance(product, dict):
                articles.append(product)

    return articles if len(articles) >= 5 else []


def _parse_article_elements(html):
    """Parst <article class='aditem'> Elemente aus HTML.

    Extrahiert Name, Preis, URL, Ort und Distanz aus jedem Artikel.
    """
    article_matches = re.finditer(
        r'<article[^>]*class="[^"]*aditem[^"]*"[^>]*>(.*?)</article>',
        html, re.DOTALL
    )

    articles = []
    for m in article_matches:
        article_tag = m.group(0)
        article_html = m.group(1)
        article = {}

        # data-href extrahieren – steht AUF dem <article>-Tag, nicht im Content
        data_href = re.search(r'data-href="(/s-anzeige/[^"]+)"', article_tag)
        if data_href:
            article['url'] = KA_BASE + data_href.group(1)
        else:
            # Fallback: href im Content
            link_match = re.search(r'href="(/s-anzeige/[^"]+)"', article_html)
            if link_match:
                article['url'] = KA_BASE + link_match.group(1)

        # JSON-LD im Article-Scope
        jld_in_article = re.search(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            article_html, re.DOTALL
        )
        if jld_in_article:
            try:
                jld_data = json.loads(jld_in_article.group(1))
                if isinstance(jld_data, dict):
                    article['_jsonld'] = jld_data
                    article['name'] = jld_data.get('title') or jld_data.get('name', '')
                    if not article.get('url'):
                        url_jld = jld_data.get('url', '')
                        if url_jld:
                            article['url'] = (
                                url_jld if url_jld.startswith('http')
                                else KA_BASE + url_jld
                            )
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

    return articles


def _deduplicate_and_enrich(articles):
    """Dedupliziert Artikel nach URL und reichert mit PLZ-Info an."""
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
                offers = jld.get('offers', {})
                if isinstance(offers, dict):
                    seller = offers.get('seller', {})
                    if isinstance(seller, dict):
                        addr = seller.get('address', {})
                        if isinstance(addr, dict):
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

        # Preise normalisieren
        if a.get('price') is None:
            a['price'] = None

        unique_articles.append(a)

    return unique_articles


def fetch_kleinanzeigen(search_term, max_price=None, plz=None, radius=None):
    """Ruft die Kleinanzeigen-Suche auf und parst die Ergebnisse.

    Args:
        search_term: Suchbegriff
        max_price: Optionaler Maximalpreis
        plz: Optionale PLZ für Standort
        radius: Optionaler Radius in km

    Returns:
        Liste von Dicts mit Artikeldaten (name, price, url, location, ...)
        oder leere Liste bei Fehler/IP-Block.
    """
    url = build_search_url(search_term, max_price, plz, radius)

    html = _fetch_html(url)
    if html is None:
        return []  # IP block or error

    # Methode 1: JSON-LD ItemList
    articles = _parse_jsonld(html)

    if len(articles) < 5:
        # Methode 2: <article> Elemente parsen
        articles = _parse_article_elements(html)

    # Deduplizieren und anreichern
    articles = _deduplicate_and_enrich(articles)

    return articles
