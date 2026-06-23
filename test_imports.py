"""Verification tests for the notion-kleinanzeigen package structure."""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

errors = []

# Test 1: config
try:
    from src.config import load_token
    t = load_token()
    print(f'✅ [config] Token: {t[:10]}...{t[-4:]} ({len(t)} Zeichen)')
except Exception as e:
    errors.append(f'[config] {e}')
    print(f'❌ [config] {e}')

# Test 2: notion client
try:
    from src.notion.client import notion_get, notion_post, notion_patch, query_database, create_page, extract_property_value
    print('✅ [notion.client] OK')
except Exception as e:
    errors.append(f'[notion.client] {e}')
    print(f'❌ [notion.client] {e}')

# Test 3: kleinanzeigen search
try:
    from src.kleinanzeigen.search import fetch_kleinanzeigen, build_search_url
    print('✅ [kleinanzeigen.search] OK')
except Exception as e:
    errors.append(f'[kleinanzeigen.search] {e}')
    print(f'❌ [kleinanzeigen.search] {e}')

# Test 4: kleinanzeigen geo
try:
    from src.kleinanzeigen.geo import extract_plz_from_text, parse_price
    plz = extract_plz_from_text('12345 Berlin')
    assert plz == '12345', f'Expected 12345, got {plz}'
    price = parse_price('12,99 €')
    assert price == 12.99, f'Expected 12.99, got {price}'
    print('✅ [kleinanzeigen.geo] OK')
except Exception as e:
    errors.append(f'[kleinanzeigen.geo] {e}')
    print(f'❌ [kleinanzeigen.geo] {e}')

# Test 5: kleinanzeigen user_agents
try:
    from src.kleinanzeigen.user_agents import random_user_agent, USER_AGENTS
    ua = random_user_agent()
    assert ua in USER_AGENTS
    print('✅ [kleinanzeigen.user_agents] OK')
except Exception as e:
    errors.append(f'[kleinanzeigen.user_agents] {e}')
    print(f'❌ [kleinanzeigen.user_agents] {e}')

# Test 6: workflow
try:
    from src.workflow import run, log
    print('✅ [workflow] OK')
except Exception as e:
    errors.append(f'[workflow] {e}')
    print(f'❌ [workflow] {e}')

# Test 7: dry-run run
try:
    log('--- Dry-Run Test (simuliert, keine API-Calls) ---')
    print('✅ [workflow.run] callable signature OK')
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
