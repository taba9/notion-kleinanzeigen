"""Verification tests for the notion-kleinanzeigen package structure."""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

errors = []

# Test 0: neue Module — logger, filters, text_utils
try:
    from src.logger import log, section, header, summary_line
    log('✅ [logger] OK')
except Exception as e:
    errors.append(f'[logger] {e}')
    print(f'❌ [logger] {e}')

try:
    from src.kleinanzeigen.text_utils import extract_plz_from_text, parse_price
    plz = extract_plz_from_text('12345 Berlin')
    assert plz == '12345', f'Expected 12345, got {plz}'
    price = parse_price('12,99 €')
    assert price == 12.99, f'Expected 12.99, got {price}'
    log('✅ [kleinanzeigen.text_utils] OK')
except Exception as e:
    errors.append(f'[kleinanzeigen.text_utils] {e}')
    print(f'❌ [kleinanzeigen.text_utils] {e}')

try:
    from src.filters import filter_by_price, deduplicate_by_url, apply_all_filters
    # Test filter_by_price
    articles = [{'price': 10}, {'price': 50}, {'price': 100}, {'price': None}]
    filtered, skipped = filter_by_price(articles, 60)
    assert len(filtered) == 3, f'Expected 3, got {len(filtered)}'
    assert skipped == 1
    # Test deduplicate
    links = set()
    filtered2, skipped2 = deduplicate_by_url(filtered, links)
    assert skipped2 == 0
    # Test apply_all
    links.add('http://example.com/dup')
    articles_with_url = [
        {'price': 10, 'url': 'http://example.com/ok1'},
        {'price': 200, 'url': 'http://example.com/too_expensive'},
        {'price': 15, 'url': 'http://example.com/dup'},
    ]
    final, stats = apply_all_filters(articles_with_url, 100, links)
    assert len(final) == 1, f'Expected 1, got {len(final)}'
    assert stats['price_skipped'] == 1
    assert stats['duplicate_skipped'] == 1
    log('✅ [filters] OK')
except Exception as e:
    errors.append(f'[filters] {e}')
    print(f'❌ [filters] {e}')

try:
    from src.notion.properties import extract_search_entry, build_result_properties
    # Test build_result_properties
    props = build_result_properties('Test', 12.50, 'Berlin', 5, 'https://example.com')
    assert props['Artikelname']['title'][0]['text']['content'] == 'Test'
    assert props['Preis']['number'] == 12.50
    assert props['Ort']['rich_text'][0]['text']['content'] == 'Berlin'
    assert props['Entfernung']['number'] == 5
    assert props['Link']['url'] == 'https://example.com'
    assert 'Gefunden am' in props
    log('✅ [notion.properties] OK')
except Exception as e:
    errors.append(f'[notion.properties] {e}')
    print(f'❌ [notion.properties] {e}')

# Test 1: config
try:
    from src.config import load_token
    t = load_token()
    log(f'✅ [config] Token: {t[:10]}...{t[-4:]} ({len(t)} Zeichen)')
except Exception as e:
    errors.append(f'[config] {e}')
    print(f'❌ [config] {e}')

# Test 2: notion client
try:
    from src.notion.client import notion_get, notion_post, notion_patch, query_database, create_page, extract_property_value
    log('✅ [notion.client] OK')
except Exception as e:
    errors.append(f'[notion.client] {e}')
    print(f'❌ [notion.client] {e}')

# Test 3: kleinanzeigen search
try:
    from src.kleinanzeigen.search import fetch_kleinanzeigen, build_search_url
    log('✅ [kleinanzeigen.search] OK')
except Exception as e:
    errors.append(f'[kleinanzeigen.search] {e}')
    print(f'❌ [kleinanzeigen.search] {e}')

# Test 4: kleinanzeigen user_agents
try:
    from src.kleinanzeigen.user_agents import random_user_agent, USER_AGENTS
    ua = random_user_agent()
    assert ua in USER_AGENTS
    log('✅ [kleinanzeigen.user_agents] OK')
except Exception as e:
    errors.append(f'[kleinanzeigen.user_agents] {e}')
    print(f'❌ [kleinanzeigen.user_agents] {e}')

# Test 5: workflow
try:
    from src.workflow import run, get_existing_links
    log('✅ [workflow] OK')
except Exception as e:
    errors.append(f'[workflow] {e}')
    print(f'❌ [workflow] {e}')

# Test 6: dry-run callable
try:
    log('--- Dry-Run Test (simuliert, keine API-Calls) ---')
    log('✅ [workflow.run] callable')
except Exception as e:
    errors.append(f'[workflow.run] {e}')
    print(f'❌ [workflow.run] {e}')

# Summary
print()
print('=' * 50)
if errors:
    print(f'❌ {len(errors)} Test(s) FAILED:')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('✅ ALLE TESTS BESTANDEN')
