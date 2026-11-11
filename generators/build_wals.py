#!/usr/bin/env python3
"""Build data/wals.json for the language stream from the WALS CLDF tables.

Run by hand when the data should be refreshed:

    python3 build_wals.py /path/to/cldf

where the directory holds languages.csv, values.csv, codes.csv, parameters.csv
and countries.csv from https://github.com/cldf-datasets/wals (CC BY 4.0).
Only the features listed in FEATURES are kept, and only languages that have
at least MIN_FEATURES of them.
"""
import csv, json, os, sys

# WALS feature ids, in the order a card should prefer them.
FEATURES = [
    '81A', '138A', '129A', '130A', '131A', '132A', '134A', '13A', '1A', '2A',
    '12A', '30A', '49A', '77A', '45A', '44A', '37A', '38A', '26A', '85A',
    '87A', '66A', '67A', '112A', '116A', '107A', '136A', '142A', '119A',
]
MIN_FEATURES = 8


def rows(directory, name):
    with open(os.path.join(directory, name), newline='', encoding='utf-8') as f:
        yield from csv.DictReader(f)


def main(directory):
    keep = set(FEATURES)
    params = {r['ID']: r['Name'] for r in rows(directory, 'parameters.csv') if r['ID'] in keep}
    codes = {r['ID']: r['Name'] for r in rows(directory, 'codes.csv') if r['Parameter_ID'] in keep}
    countries = {r['ID']: r['Name'] for r in rows(directory, 'countries.csv')}

    values = {}
    for r in rows(directory, 'values.csv'):
        if r['Parameter_ID'] in keep and r['Code_ID'] in codes:
            values.setdefault(r['Language_ID'], {})[r['Parameter_ID']] = codes[r['Code_ID']]

    languages = []
    for r in rows(directory, 'languages.csv'):
        feats = values.get(r['ID'], {})
        if len(feats) < MIN_FEATURES or not r['Family']:
            continue
        languages.append({
            'id': r['ID'],
            'name': r['Name'],
            'family': r['Family'],
            'genus': r['Genus'],
            'macroarea': r['Macroarea'],
            'countries': [countries.get(c, c) for c in r['Country_ID'].split() if c],
            'iso': r['ISO639P3code'],
            'glottocode': r['Glottocode'],
            'lat': round(float(r['Latitude']), 2) if r['Latitude'] else None,
            'lon': round(float(r['Longitude']), 2) if r['Longitude'] else None,
            'features': {k: feats[k] for k in FEATURES if k in feats},
        })

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'wals.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            'source': 'Dryer, Matthew S. & Haspelmath, Martin (eds.) 2013. The World Atlas of '
                      'Language Structures Online. Leipzig: Max Planck Institute for Evolutionary '
                      'Anthropology. https://wals.info (CC BY 4.0)',
            'features': {k: params[k] for k in FEATURES},
            'languages': languages,
        }, f, ensure_ascii=False, separators=(',', ':'))
    print(f"{len(languages)} languages, {os.path.getsize(out) // 1024} KB -> {out}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
