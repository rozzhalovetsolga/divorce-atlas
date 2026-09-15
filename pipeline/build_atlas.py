import glob
import html as html_lib
import json
import os
import re

S = os.path.dirname(os.path.abspath(__file__))
WIKI_URL = 'https://en.wikipedia.org/wiki/List_of_countries_by_marriage_and_divorce_rates'
# Rows whose divorce counts omit court divorces, so the ratio is not comparable with other countries.
EXCLUDE = {('CN', 2025), ('MA', 2024)}


def norm(name):
    return re.sub(r'[^a-z]', '', name.lower())


iso = json.load(open(f'{S}/iso.json'))
name_to_a2 = {norm(c['name']): c['alpha-2'] for c in iso}
num_to_a2 = {c['country-code']: c['alpha-2'] for c in iso}
ALIASES = {
    'russia': 'RU', 'iran': 'IR', 'southkorea': 'KR', 'korea': 'KR', 'northkorea': 'KP', 'taiwan': 'TW',
    'vietnam': 'VN', 'czechrepublic': 'CZ', 'czechia': 'CZ', 'moldova': 'MD', 'syria': 'SY',
    'venezuela': 'VE', 'bolivia': 'BO', 'tanzania': 'TZ', 'laos': 'LA', 'macau': 'MO', 'macao': 'MO',
    'hongkong': 'HK', 'unitedstates': 'US', 'usa': 'US', 'unitedkingdom': 'GB', 'uk': 'GB',
    'turkey': 'TR', 'turkiye': 'TR', 'trkiye': 'TR', 'brunei': 'BN', 'kosovo': 'XK',
    'bosniaandherzegovina': 'BA', 'northmacedonia': 'MK', 'palestine': 'PS', 'uae': 'AE',
    'unitedarabemirates': 'AE', 'netherlands': 'NL', 'saintvincentandthegrenadines': 'VC',
    'saintlucia': 'LC', 'bahamas': 'BS', 'cotedivoire': 'CI', 'dominicanrepublic': 'DO',
    'puertorico': 'PR', 'guam': 'GU', 'gibraltar': 'GI', 'bermuda': 'BM', 'faroeislands': 'FO',
    'greenland': 'GL', 'curacao': 'CW', 'capeverde': 'CV', 'caboverde': 'CV', 'eswatini': 'SZ',
    'englandandwales': 'GB', 'hongkongsar': 'HK', 'macaosar': 'MO',
}


def a2_of(name):
    key = norm(name)
    if key in ALIASES:
        return ALIASES[key]
    if key in name_to_a2:
        return name_to_a2[key]
    for alias, code in ALIASES.items():
        if key.startswith(alias):
            return code
    return None


def year_of(value):
    match = re.search(r'\d{4}', str(value))
    return int(match.group(0)) if match else None


def num(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


candidates = []
for row in json.load(open(f'{S}/wiki_rows.json')):
    candidates.append({
        'name_en': row['country'],
        'year': row['year'],
        'mr': row['marriage'],
        'dr': row['divorce'],
        'marriages': None,
        'divorces': None,
        'ratio': None,
        'src': WIKI_URL,
        'note_en': None,
        'fresh': False,
    })
for path in sorted(glob.glob(f'{S}/fresh_*.json')):
    for row in json.load(open(path)):
        candidates.append({
            'name_en': row['country'],
            'year': year_of(row.get('year')),
            'mr': num(row.get('marriage_rate')),
            'dr': num(row.get('divorce_rate')),
            'marriages': num(row.get('marriages')),
            'divorces': num(row.get('divorces')),
            'ratio': num(row.get('ratio_pct')),
            'src': row.get('source') or '',
            'note_en': row.get('note'),
            'fresh': True,
        })

NOTES_RU = json.load(open(f'{S}/notes_ru.json')) if os.path.exists(f'{S}/notes_ru.json') else {}

best = {}
eu = None
unmatched = []
for row in candidates:
    if row['year'] is None:
        continue
    if row['ratio'] is not None:
        pass
    elif row['marriages'] and row['divorces']:
        row['ratio'] = round(row['divorces'] / row['marriages'] * 100, 1)
    elif row['mr'] and row['dr']:
        row['ratio'] = round(row['dr'] / row['mr'] * 100, 1)
    if row['ratio'] is None and row['dr'] is None:
        continue
    if norm(row['name_en']) == 'europeanunion':
        if eu is None or (row['year'], row['fresh']) > (eu['year'], eu['fresh']):
            eu = row
        continue
    code = a2_of(row['name_en'])
    if not code:
        unmatched.append(row['name_en'])
        continue
    if (code, row['year']) in EXCLUDE:
        continue
    row['iso2'] = code
    current = best.get(code)
    if current is None or (row['year'], row['fresh']) > (current['year'], current['fresh']):
        best[code] = row

rows = sorted(best.values(), key=lambda row: -(row['ratio'] or 0))
for row in rows:
    row['note'] = NOTES_RU.get(row['iso2'])
print('countries', len(rows), 'unmatched', unmatched)
for row in rows:
    tag = 'fresh' if row['fresh'] else 'wiki'
    print(f"{row['iso2']} {row['name_en']:<24} {row['year']} ratio={row['ratio']} dr={row['dr']} mr={row['mr']} {tag} | {row['note_en'] or ''}"[:220])

public_keys = ['iso2', 'name_en', 'year', 'mr', 'dr', 'marriages', 'divorces', 'ratio', 'src', 'note']
public_rows = [{key: row.get(key) for key in public_keys} for row in rows]
eu_public = {key: eu.get(key) for key in public_keys} if eu else None
json.dump(public_rows, open(f'{S}/world_rows.json', 'w'), ensure_ascii=False)

hosts = set()
for row in rows:
    if row['fresh']:
        for url in (row['src'] or '').split(';'):
            url = url.strip()
            if url.startswith('http'):
                hosts.add(re.sub(r'^https?://(www\.)?', '', url).split('/')[0])
sources_html = ''
if hosts:
    sources_html = ('<li>Данные 2023–2026 гг. (национальные статслужбы, Eurostat): '
                    + html_lib.escape(', '.join(sorted(hosts)))
                    + '. Ссылка на конкретную публикацию — в колонке «Источник» таблицы.</li>')

class MultiPage:
    def __init__(self, texts):
        self.texts = texts

    def replace(self, old, new):
        return MultiPage([text.replace(old, new) for text in self.texts])


page = MultiPage([open(f'{S}/template_map.html').read(), open(f'{S}/template_lean.html').read()])
page = page.replace('/*CSS*/', open(f'{S}/new_style.css').read())
page = page.replace('/*DATA*/', json.dumps(public_rows, ensure_ascii=False))
page = page.replace('/*EU*/', json.dumps(eu_public, ensure_ascii=False))
page = page.replace('/*TOPO110*/', open(f'{S}/countries-110m.json').read())
page = page.replace('/*TOPO50*/', open(f'{S}/countries-50m.json').read())
page = page.replace('/*NUM2A2*/', json.dumps(num_to_a2))
page = page.replace('/*SOURCES*/', sources_html)

us_acs = json.load(open(f'{S}/us_acs_2024.json'))
us_cdc_by_name = json.load(open(f'{S}/us_cdc_2023.json'))
name_to_fips = {row['name']: row['fips'] for row in us_acs}
us_cdc = {}
for name, rates in us_cdc_by_name.items():
    fips = name_to_fips.get(name)
    if fips and fips != 'US':
        us_cdc[fips] = rates
cdc_us = us_cdc_by_name.get('United States') or {'mr': 6.1, 'dr': 2.4}
print('us states', len(us_acs) - 1, 'cdc matched', len(us_cdc), 'cdc national', cdc_us)
page = page.replace('/*US_DATA*/', json.dumps({'acs': us_acs, 'cdc': us_cdc, 'cdc_us': cdc_us}, ensure_ascii=False))
page = page.replace('/*US_TOPO*/', open(f'{S}/states-albers-10m.json').read())

CAUSE_FILES = {
    'causes_reasons.json': 'reasons',
    'causes_risk.json': 'risk',
    'causes_psych.json': 'risk',
    'causes_macro.json': 'macro',
    'causes_parental.json': 'parental',
}
causes = []
for filename, section in CAUSE_FILES.items():
    path = f'{S}/{filename}'
    if not os.path.exists(path):
        continue
    for item in json.load(open(path)):
        item['section'] = 'time' if item.get('group') == 'время и динамика' else section
        causes.append(item)
print('causes', len(causes))
page = page.replace('/*CAUSES*/', json.dumps(causes, ensure_ascii=False).replace('</', '<\\/'))
page = page.replace('/*CAUSES_COUNT*/', str(len(causes)))
page = page.replace('/*AN_WORLD*/', open(f'{S}/analysis_world.json').read())
page = page.replace('/*AN_US*/', open(f'{S}/analysis_us.json').read())

duration_es = json.load(open(f'{S}/duration_eurostat.json'))
duration_nat = json.load(open(f'{S}/duration_national.json')) if os.path.exists(f'{S}/duration_national.json') else []
for series in duration_nat:
    series['iso2'] = a2_of(series.get('country') or '') or ''
print('duration eurostat', len(duration_es), 'national series', len(duration_nat))
page = page.replace('/*DURATION_ES*/', json.dumps(duration_es, ensure_ascii=False))
page = page.replace('/*DURATION_NAT*/', json.dumps(duration_nat, ensure_ascii=False).replace('</', '<\\/'))

by_data = json.load(open(f'{S}/belarus_data.json')) if os.path.exists(f'{S}/belarus_data.json') else {}
us_deep = json.load(open(f'{S}/usa_data.json')) if os.path.exists(f'{S}/usa_data.json') else {}
print('belarus', {k: len(v) for k, v in by_data.items() if isinstance(v, list)}, 'usa', {k: len(v) for k, v in us_deep.items() if isinstance(v, list)})
page = page.replace('/*BY_DATA*/', json.dumps(by_data, ensure_ascii=False).replace('</', '<\\/'))
page = page.replace('/*BY_GEO*/', open(f'{S}/blr_adm1_small.json').read())
page = page.replace('/*US_DEEP*/', json.dumps(us_deep, ensure_ascii=False).replace('</', '<\\/'))
os.makedirs(f'{S}/build', exist_ok=True)
open(f'{S}/build/appendix.html', 'w').write(page.texts[0])
open(f'{S}/build/index.html', 'w').write(page.texts[1])
print('wrote build/appendix.html', len(page.texts[0]), 'build/index.html', len(page.texts[1]))
