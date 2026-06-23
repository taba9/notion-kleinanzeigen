"""Notion API Client — reiner Wrapper für die Notion REST API.

Enthält ausschließlich Notion-API-Kommunikation.
Importiert NIEMALS aus src/kleinanzeigen/.
"""

import json
import urllib.request
import urllib.error

from ..config import NOTION_VERSION, BASE_URL, PAGE_SIZE, load_token


_DEFAULT_TOKEN = None


def _get_token(token=None):
    """Interner Helfer: lädt Token bei Bedarf."""
    global _DEFAULT_TOKEN
    if token:
        return token
    if _DEFAULT_TOKEN is None:
        _DEFAULT_TOKEN = load_token()
    return _DEFAULT_TOKEN


def notion_api(endpoint, data=None, method='POST', token=None):
    """Führt einen Notion-API-Aufruf aus.

    Args:
        endpoint: API-Endpunkt (z.B. 'databases/{id}/query')
        data: Dict mit den zu sendenden Daten (wird als JSON serialisiert)
        method: HTTP-Methode (POST, GET, PATCH)
        token: Notion-API-Token (optional, wird bei Bedarf geladen)

    Returns:
        Tuple (status_code, parsed_response_dict)
    """
    token = _get_token(token)
    url = f'{BASE_URL}/{endpoint}'
    payload = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=payload, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Notion-Version', NOTION_VERSION)
    if payload:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode('utf-8')
            parsed = json.loads(raw)
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {'message': body[:200]}
        return e.code, parsed
    except Exception as e:
        return 0, {'message': str(e)}


def notion_get(endpoint, token=None):
    """GET-Anfrage an die Notion-API."""
    return notion_api(endpoint, data=None, method='GET', token=token)


def notion_post(endpoint, data, token=None):
    """POST-Anfrage an die Notion-API."""
    return notion_api(endpoint, data=data, method='POST', token=token)


def notion_patch(endpoint, data, token=None):
    """PATCH-Anfrage an die Notion-API."""
    return notion_api(endpoint, data=data, method='PATCH', token=token)


def query_database(db_id, filter_data=None, token=None):
    """Alle Einträge aus einer Notion-Datenbank abfragen (mit Paginierung).

    Args:
        db_id: Datenbank-ID
        filter_data: Optionaler Filter (Dict)
        token: Notion-API-Token

    Returns:
        Liste aller Einträge (Seiten)
    """
    all_results = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {'page_size': PAGE_SIZE}
        if filter_data:
            payload['filter'] = filter_data
        if next_cursor:
            payload['start_cursor'] = next_cursor

        status, data = notion_api(
            f'databases/{db_id}/query', payload, token=token
        )
        if status >= 400 or data.get('object') == 'error':
            raise RuntimeError(
                f'Fehler beim Abfragen der DB: {data.get("message", "?")}'
            )

        results = data.get('results', [])
        all_results.extend(results)
        has_more = data.get('has_more', False)
        next_cursor = data.get('next_cursor')

    return all_results


def extract_property_value(properties, prop_name):
    """Extrahiert den Wert einer Notion-Property anhand ihres Namens.

    Unterstützt: title, rich_text, number, url, select, multi_select,
    status, date, checkbox.
    """
    prop = properties.get(prop_name, {})
    ptype = prop.get('type', '?')

    if ptype == 'title':
        texts = prop.get('title', [])
        return ''.join(t.get('plain_text', '') for t in texts)
    elif ptype == 'rich_text':
        texts = prop.get('rich_text', [])
        return ''.join(t.get('plain_text', '') for t in texts)
    elif ptype == 'number':
        return prop.get('number')
    elif ptype == 'url':
        return prop.get('url', '')
    elif ptype == 'select':
        s = prop.get('select')
        return s['name'] if s else None
    elif ptype == 'multi_select':
        items = [s['name'] for s in prop.get('multi_select', [])]
        return items
    elif ptype == 'status':
        s = prop.get('status')
        return s['name'] if s else None
    elif ptype == 'date':
        d = prop.get('date')
        return d['start'] if d else None
    elif ptype == 'checkbox':
        return prop.get('checkbox', False)
    else:
        return prop.get(ptype, None)


def create_page(database_id, properties, token=None):
    """Erstellt eine neue Seite in einer Notion-Datenbank.

    Args:
        database_id: Ziel-Datenbank-ID
        properties: Dict der Property-Werte (im Notion-API-Format)
        token: Notion-API-Token

    Returns:
        Die erstellte Seite (Dict) oder None bei Fehler
    """
    data = {
        'parent': {'database_id': database_id},
        'properties': properties,
    }
    status, resp = notion_api('pages', data, token=token)
    if status in (200, 201):
        return resp
    else:
        raise RuntimeError(
            f'Fehler beim Erstellen der Seite: {resp.get("message", "?")}'
        )


def update_page(page_id, properties, token=None):
    """Aktualisiert eine bestehende Notion-Seite.

    Args:
        page_id: Seiten-ID
        properties: Dict der Property-Werte (im Notion-API-Format)
        token: Notion-API-Token

    Returns:
        Die aktualisierte Seite (Dict) oder None bei Fehler
    """
    data = {'properties': properties}
    status, resp = notion_patch(f'pages/{page_id}', data, token=token)
    if status in (200, 201):
        return resp
    else:
        raise RuntimeError(
            f'Fehler beim Aktualisieren der Seite: {resp.get("message", "?")}'
        )
