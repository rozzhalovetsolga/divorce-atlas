"""US state metrics (ACS), country correlates (World Bank, WHO), religion (Wikipedia/Pew/Gallup) and Spearman correlations.

Inputs: raw/census, raw/worldbank, raw/who, raw/wikipedia, iso.json and world_rows.json (written by build_atlas.py).
Outputs: us_acs_2024.json, us_covariates_2024.json, religion_world.json, religion_us.json, analysis_world.json, analysis_us.json.
"""
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE


def out(name, data):
    json.dump(data, open(os.path.join(OUT, name), 'w'), ensure_ascii=False)


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            result[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return result


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return sxy / math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


def residuals(y, controls):
    """Residuals of an OLS regression of y on the controls (with intercept)."""
    rows = [[1.0] + [control[i] for control in controls] for i in range(len(y))]
    k = len(rows[0])
    matrix = [[sum(rows[r][i] * rows[r][j] for r in range(len(y))) for j in range(k)] + [sum(rows[r][i] * y[r] for r in range(len(y)))] for i in range(k)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(matrix[r][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        for r in range(k):
            if r != col:
                factor = matrix[r][col] / matrix[col][col]
                matrix[r] = [a - factor * b for a, b in zip(matrix[r], matrix[col])]
    beta = [matrix[i][k] / matrix[i][i] for i in range(k)]
    return [y[i] - sum(beta[j] * rows[i][j] for j in range(k)) for i in range(len(y))]


# 1. US states: ACS 2024 1-year via Census Reporter
census = json.load(open(os.path.join(RAW, 'census', 'cr_states.json')))
us_rows = []
for geoid, tables in census['data'].items():
    marriages = int(tables['B12501']['estimate']['B12501010'])
    divorces = int(tables['B12503']['estimate']['B12503010'])
    married_women = int(tables['B12001']['estimate']['B12001013'])
    divorces_moe = int(tables['B12503']['error']['B12503010'])
    us_rows.append({
        'geoid': geoid,
        'fips': geoid[-2:] if geoid != '01000US' else 'US',
        'name': census['geography'][geoid]['name'],
        'marriages': marriages,
        'marriages_moe': int(tables['B12501']['error']['B12501010']),
        'divorces': divorces,
        'divorces_moe': divorces_moe,
        'married_women': married_women,
        'ratio': round(divorces / marriages * 100, 1),
        'refined': round(divorces / married_women * 1000, 1),
        'div_moe_pct': round(divorces_moe / divorces * 100),
    })
out('us_acs_2024.json', us_rows)

covariates_raw = json.load(open(os.path.join(RAW, 'census', 'cr_covariates.json')))
covariates = {}
for geoid, tables in covariates_raw['data'].items():
    education = tables['B15003']['estimate']
    bachelor = sum(education[f'B15003{n:03d}'] for n in (22, 23, 24, 25)) / education['B15003001'] * 100
    covariates[geoid[-2:] if geoid != '01000US' else 'US'] = {
        'name': covariates_raw['geography'][geoid]['name'],
        'age_first_marriage_f': tables['B12007']['estimate'].get('B12007002'),
        'age_first_marriage_m': tables['B12007']['estimate'].get('B12007001'),
        'median_income': tables['B19013']['estimate']['B19013001'],
        'bachelor_pct': round(bachelor, 1),
        'median_age': tables['B01002']['estimate']['B01002001'],
    }
out('us_covariates_2024.json', covariates)

# 2. Countries: latest divorce data (not older than 2015, estimates excluded) + World Bank + WHO
iso = json.load(open(os.path.join(HERE, 'iso.json')))
a2_to_a3 = {c['alpha-2']: c['alpha-3'] for c in iso}
a3_to_a2 = {c['alpha-3']: c['alpha-2'] for c in iso}
region_of = {c['alpha-2']: c['region'] for c in iso}
world = [row for row in json.load(open(os.path.join(HERE, 'world_rows.json'))) if row['year'] >= 2015 and row['iso2'] not in ('IN', 'VN', 'VE')]


def latest_wb(code):
    rows = json.load(open(os.path.join(RAW, 'worldbank', f'{code}.json')))[1]
    return {r['countryiso3code']: (r['value'], int(r['date'])) for r in rows if r['value'] is not None and r['countryiso3code']}


indicators = {
    'age_marriage_f': ('Возраст первого брака женщин', latest_wb('SP.DYN.SMAM.FE')),
    'female_lfp': ('Занятость женщин, % женщин 15+', latest_wb('SL.TLF.CACT.FE.ZS')),
    'gdp_ppp': ('ВВП на душу по ППС, $', latest_wb('NY.GDP.PCAP.PP.KD')),
    'urban': ('Городское население, %', latest_wb('SP.URB.TOTL.IN.ZS')),
    'fertility': ('Рождаемость, детей на женщину', latest_wb('SP.DYN.TFRT.IN')),
    'tertiary_f': ('Женщины в вузах, валовой охват %', latest_wb('SE.TER.ENRR.FE')),
    'age65': ('Население 65+, %', latest_wb('SP.POP.65UP.TO.ZS')),
}
alcohol = {}
for record in json.load(open(os.path.join(RAW, 'who', 'who_SA_0000001688.json')))['value']:
    code, year, value = record['SpatialDim'], record['TimeDim'], record['NumericValue']
    if value is not None and (code not in alcohol or year > alcohol[code][1]):
        alcohol[code] = (value, year)
indicators['alcohol'] = ('Алкоголь, литров на душу 15+', alcohol)

# 3. Religion by country (Wikipedia tables; Gallup importance of religion)
norm = lambda s: re.sub(r'[^a-z]', '', s.lower())
name_to_a2 = {norm(c['name']): c['alpha-2'] for c in iso}
ALIASES = {'russia': 'RU', 'iran': 'IR', 'southkorea': 'KR', 'northkorea': 'KP', 'taiwan': 'TW', 'vietnam': 'VN',
           'czechrepublic': 'CZ', 'czechia': 'CZ', 'moldova': 'MD', 'syria': 'SY', 'venezuela': 'VE', 'bolivia': 'BO',
           'tanzania': 'TZ', 'laos': 'LA', 'macau': 'MO', 'hongkong': 'HK', 'unitedstates': 'US', 'unitedkingdom': 'GB',
           'turkey': 'TR', 'turkiye': 'TR', 'brunei': 'BN', 'kosovo': 'XK', 'bosniaandherzegovina': 'BA',
           'northmacedonia': 'MK', 'palestine': 'PS', 'netherlands': 'NL', 'ivorycoast': 'CI', 'cotedivoire': 'CI',
           'capeverde': 'CV', 'eswatini': 'SZ', 'swaziland': 'SZ', 'republicofthecongo': 'CG', 'democraticrepublicofthecongo': 'CD',
           'eastimor': 'TL', 'timorleste': 'TL', 'micronesia': 'FM', 'federatedstatesofmicronesia': 'FM', 'vaticancity': 'VA',
           'saintvincentandthegrenadines': 'VC', 'saintlucia': 'LC', 'saintkittsandnevis': 'KN', 'gambia': 'GM', 'thegambia': 'GM',
           'bahamas': 'BS', 'thebahamas': 'BS', 'dominicanrepublic': 'DO', 'puertorico': 'PR', 'guam': 'GU', 'unitedarabemirates': 'AE'}


def a2_of(name):
    key = norm(name)
    return ALIASES.get(key) or name_to_a2.get(key)


def wiki_text(page):
    return open(os.path.join(RAW, 'wikipedia', f'{page}.txt')).read()


def table_after(text, marker):
    start = text.find(marker)
    return text[start:text.find('\n|}', start)]


def flag_percent_table(page, marker):
    table = {}
    for row in table_after(wiki_text(page), marker).split('\n|-')[1:]:
        name = re.search(r'\{\{flag(?:icon)?\|([^}|]+)', row)
        percent = re.findall(r'(\d+(?:\.\d+)?)\s*%', row)
        if name and percent:
            code = a2_of(name.group(1))
            if code:
                table.setdefault(code, float(percent[0]))
    return table


protestant = flag_percent_table('Protestantism_by_country', 'Protestants by country')
catholic = flag_percent_table('Catholic_Church_by_country', 'Catholic Church by country')
orthodox = flag_percent_table('Eastern_Orthodoxy_by_country', '% Eastern Orthodox')
importance = {a3_to_a2[m.group(1)]: float(m.group(2))
              for m in re.finditer(r'\{\{([A-Z]{3})\}\}\s*\|\|\s*(\d+)%', wiki_text('Importance_of_religion_by_country')) if m.group(1) in a3_to_a2}
religion_world = {row['iso2']: {'prot': protestant.get(row['iso2']), 'cath': catholic.get(row['iso2']),
                                'orth': orthodox.get(row['iso2']), 'importance': importance.get(row['iso2'])} for row in world}
out('religion_world.json', religion_world)

points = []
for row in world:
    a3 = a2_to_a3.get(row['iso2'])
    point = {'iso2': row['iso2'], 'name': row['name_en'], 'ratio': row['ratio'], 'dr': row['dr'], 'year': row['year']}
    for key, (_, table) in indicators.items():
        point[key] = round(table[a3][0], 2) if a3 in table else None
    point['mr'] = row['mr']
    point['region'] = region_of.get(row['iso2'])
    point.update(religion_world[row['iso2']])
    points.append(point)
labels = {'mr': 'Браков на 1000 жителей', **{key: label for key, (label, _) in indicators.items()},
          'prot': '% протестантов', 'cath': '% католиков', 'orth': '% православных', 'importance': 'Религия важна в жизни, %'}

# 4. Religion by US state (Pew Religious Landscape Study 2023–2024, via Wikipedia)
table = table_after(wiki_text('Religion_in_the_United_States'), 'Religious Landscape Study, 2023-2024')
headers = [re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', h).strip() for h in re.findall(r'^!(.*)$', table.split('\n|-')[0], re.M)]
states_by_name = {row['name']: row for row in us_rows if row['fips'] != 'US'}
names = sorted(states_by_name, key=len, reverse=True)
religion_us = {}
for chunk in table.split('|-')[1:]:
    found = next((name for name in names if re.search(r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])', chunk)), None)
    if not found or states_by_name[found]['fips'] in religion_us:
        continue
    values = []
    for cell in re.split(r'\|\||\n\|', chunk[chunk.find(found) + len(found):]):
        cell = re.sub(r'<ref.*?</ref>|<ref[^>]*/>', '', cell).strip().strip(']').strip()
        match = re.match(r'^(<)?\s*(\d+(?:\.\d+)?)\s*%?$', cell)
        if match:
            values.append(0.5 if match.group(1) else float(match.group(2)))
    if len(values) >= len(headers) - 1:
        religion_us[states_by_name[found]['fips']] = dict(zip(headers[1:], values[:len(headers) - 1]))
out('religion_us.json', religion_us)

us_points = []
for row in us_rows:
    if row['fips'] == 'US':
        continue
    rel = religion_us.get(row['fips'], {})
    us_points.append({'fips': row['fips'], 'name': row['name'], 'ratio': row['ratio'], 'refined': row['refined'], 'moe': row['div_moe_pct'],
                      **{key: covariates[row['fips']][key] for key in ('age_first_marriage_f', 'median_income', 'bachelor_pct', 'median_age')},
                      'evangelical': rel.get('Evangelical Protestant'), 'mainline': rel.get('Mainline Protestant'),
                      'catholic': rel.get('Catholic'), 'lds': rel.get('Latter-day Saint (Mormon)')})
us_labels = {'age_first_marriage_f': 'Возраст первого брака женщин', 'median_income': 'Медианный доход домохозяйства',
             'bachelor_pct': 'Высшее образование (бакалавр+), % 25+', 'median_age': 'Медианный возраст',
             'evangelical': 'Евангелисты, %', 'mainline': 'Основные протестантские церкви, %', 'catholic': 'Католики, %', 'lds': 'Мормоны, %'}

# 5. Religion summary: Europe by dominant tradition, importance of religion, US evangelical link with controls
europe = [point for point in points if point['region'] == 'Europe']


def tradition(point):
    best = max((point[key] or 0, key) for key in ('prot', 'cath', 'orth'))
    return best[1] if best[0] >= 40 else 'other'


medians = {}
for group in ('prot', 'cath', 'orth'):
    rows = [point for point in europe if tradition(point) == group]
    medians[group] = {'n': len(rows), 'dr': statistics.median([p['dr'] for p in rows if p['dr'] is not None]),
                      'ratio': statistics.median([p['ratio'] for p in rows]), 'countries': [p['iso2'] for p in rows]}
pairs = [(p['importance'], p['dr']) for p in europe if p['importance'] is not None and p['dr'] is not None]
with_religion = [p for p in us_points if p['evangelical'] is not None]
evangelical = ranks([p['evangelical'] for p in with_religion])
refined = ranks([p['refined'] for p in with_religion])
age = ranks([p['age_first_marriage_f'] for p in with_religion])
education = ranks([p['bachelor_pct'] for p in with_religion])
income = ranks([p['median_income'] for p in with_religion])
partial = lambda controls: round(pearson(residuals(evangelical, controls), residuals(refined, controls)), 2)
religion_summary = {
    'europe_medians': medians,
    'europe_importance_dr': {'r': round(spearman(*zip(*pairs)), 2), 'n': len(pairs)},
    'us_evangelical_refined': {'r': round(pearson(evangelical, refined), 2), 'n': len(with_religion)},
    'us_partial': {'age_link': round(pearson(evangelical, age), 2), 'edu_link': round(pearson(evangelical, education), 2),
                   'income_link': round(pearson(evangelical, income), 2), 'partial_edu': partial([education]),
                   'partial_age': partial([age]), 'partial_all': partial([age, education, income]), 'n': len(with_religion)},
}
out('analysis_world.json', {'points': points, 'labels': labels, 'religion_summary': religion_summary})
out('analysis_us.json', {'points': us_points, 'labels': us_labels})
print('analysis written:', len(points), 'countries,', len(us_points), 'states,', len(religion_us), 'states with religion')
