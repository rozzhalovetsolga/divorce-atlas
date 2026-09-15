#!/usr/bin/env bash
# Refresh the raw downloads used by the analysis scripts. Run from the pipeline/ folder, then:
#   python3 build_atlas.py && python3 analysis_duration.py && python3 analysis_correlations.py && python3 build_atlas.py && python3 site_export.py
set -euo pipefail
cd "$(dirname "$0")"
UA="Mozilla/5.0 (divorce-atlas data refresh)"

# Eurostat: divorces by marriage duration and marriages by year
curl -sL "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_ndivdur?format=JSON&lang=EN&sinceTimePeriod=2019" -o raw/eurostat/demo_ndivdur.json
curl -sL "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_nind?format=JSON&lang=EN&indic_de=MARRIAGE&sinceTimePeriod=1980" -o raw/eurostat/demo_nind_mar.json

# World Bank: most recent value per country
for indicator in SL.TLF.CACT.FE.ZS NY.GDP.PCAP.PP.KD SP.URB.TOTL.IN.ZS SP.DYN.TFRT.IN SE.TER.ENRR.FE SP.POP.65UP.TO.ZS; do
  curl -sL "https://api.worldbank.org/v2/country/all/indicator/$indicator?format=json&per_page=400&mrnev=1" -o "raw/worldbank/$indicator.json"
done
for indicator in SP.DYN.SMAM.FE SP.DYN.SMAM.MA; do
  curl -sL "https://api.worldbank.org/v2/country/all/indicator/$indicator?format=json&per_page=400&mrnev=1&source=14" -o "raw/worldbank/$indicator.json"
done

# WHO: total alcohol per capita (15+)
curl -sL "https://ghoapi.azureedge.net/api/SA_0000001688" -o raw/who/who_SA_0000001688.json

# US Census ACS 1-year via Census Reporter (no API key needed)
curl -sL "https://api.censusreporter.org/1.0/data/show/latest?table_ids=B12501,B12503,B12001&geo_ids=040%7C01000US,01000US" -o raw/census/cr_states.json
curl -sL "https://api.censusreporter.org/1.0/data/show/latest?table_ids=B12007,B19013,B15003,B01002&geo_ids=040%7C01000US,01000US" -o raw/census/cr_covariates.json

# Wikipedia wikitext: religion tables and the country list of marriage and divorce rates
for page in Protestantism_by_country Catholic_Church_by_country Eastern_Orthodoxy_by_country Importance_of_religion_by_country Religion_in_the_United_States List_of_countries_by_marriage_and_divorce_rates; do
  curl -sL -A "$UA" "https://en.wikipedia.org/w/api.php?action=parse&page=$page&prop=wikitext&redirects=1&format=json&formatversion=2" \
    | python3 -c "import json, sys; print(json.load(sys.stdin)['parse']['wikitext'])" > "raw/wikipedia/$page.txt"
done

# National statistics (Belstat, Rosstat, ONS, KOSTAT and others) are collected by hand into fresh_*.json,
# belarus_data.json, usa_data.json and duration_national.json — see the source URL in every row.
echo "raw data refreshed"
