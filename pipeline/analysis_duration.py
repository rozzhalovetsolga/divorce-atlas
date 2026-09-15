"""Divorce risk by marriage duration (Eurostat): distribution, median duration, duration-specific rates and total divorce rate.

Rate for duration d in year t = divorces at duration d in year t / marriages in year t−d × 1000.
Total divorce rate = sum of those rates: the share of marriages that would end in divorce at current risks.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw', 'eurostat')
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE

SKIP = {'EU27_2020', 'EU28', 'EU27_2007', 'EEA31', 'EEA30_2007', 'EFTA', 'DE_TOT', 'FX'}
GEO_TO_A2 = {'UK': 'GB', 'EL': 'GR'}
BANDS = [('0-4', range(0, 5)), ('5-9', range(5, 10)), ('10-14', range(10, 15)),
         ('15-19', range(15, 20)), ('20-24', range(20, 25)), ('25-29', range(25, 30))]


def load(path):
    data = json.load(open(path))
    dims, sizes = data['id'], data['size']
    index = {key: data['dimension'][key]['category']['index'] for key in dims}

    def get(**coords):
        position = 0
        for key, size in zip(dims, sizes):
            offset = index[key].get(str(coords[key])) if key in coords else 0
            if offset is None:
                return None
            position = position * size + offset
        return data['value'].get(str(position))
    return index, get


divorce_index, divorces_at = load(os.path.join(RAW, 'demo_ndivdur.json'))
_, marriages_in = load(os.path.join(RAW, 'demo_nind_mar.json'))

results = []
for geo in divorce_index['geo']:
    if geo in SKIP:
        continue
    for year in (2024, 2023, 2022, 2021):
        total = divorces_at(geo=geo, time=year, duration='TOTAL')
        singles = {0: divorces_at(geo=geo, time=year, duration='Y_LT1')}
        for d in range(1, 30):
            singles[d] = divorces_at(geo=geo, time=year, duration=f'Y{d}')
        if total and all(singles[d] is not None for d in range(0, 20)):
            break
    else:
        continue
    ge30 = divorces_at(geo=geo, time=year, duration='Y_GE30') or 0
    unknown = divorces_at(geo=geo, time=year, duration='UNK') or 0
    known = total - unknown
    have_29 = all(singles[d] is not None for d in range(20, 30))
    bands = {}
    for label, years in BANDS:
        if all(singles[d] is not None for d in years):
            bands[label] = round(sum(singles[d] for d in years) / known * 100, 1)
    if have_29:
        bands['30+'] = round(ge30 / known * 100, 1)
    cumulative = 0.0
    median = None
    for d in range(0, 30):
        if singles[d] is None:
            break
        share = singles[d] / known
        if cumulative + share >= 0.5:
            median = round(d + (0.5 - cumulative) / share, 1)
            break
        cumulative += share
    scale = total / known if known else 1
    rates = []
    for d in range(0, 30):
        marriages = marriages_in(geo=geo, time=year - d)
        if singles[d] is None or not marriages:
            break
        rates.append(round(singles[d] * scale / marriages * 1000, 2))
    tdr = None
    if len(rates) == 30:
        tail_marriages = marriages_in(geo=geo, time=year - 32)
        tail = ge30 * scale / tail_marriages * 1000 if tail_marriages else 0
        tdr = round((sum(rates) + tail) / 10, 1)
    peak = max(range(len(rates)), key=lambda d: rates[d]) if rates else None
    row = {'geo': geo, 'iso2': GEO_TO_A2.get(geo, geo), 'year': year, 'total': total, 'unknown': unknown,
           'bands': bands, 'median': median, 'rates': rates, 'peak_duration': peak, 'tdr': tdr, 'tdr_note': None}
    if row['tdr'] is None and len(rates) >= 25:
        row['tdr'] = round(sum(rates) / 10, 1)
        row['tdr_note'] = f'по стажу 0–{len(rates) - 1} лет, без более долгих браков — занижено'
    if len(rates) < 10:
        row['rates'] = []
    results.append(row)

json.dump(results, open(os.path.join(OUT, 'duration_eurostat.json'), 'w'), ensure_ascii=False)
print('duration_eurostat.json:', len(results), 'countries')
