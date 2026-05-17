# Sydney Suburb Investment Scorecard

A persona-weighted composite score that turns the ~700+ suburbs of Greater
Sydney into a ranked shortlist for a first-home-buyer. Built solo on
public-only data sources (ABS, NSW Valuer General, BOCSAR).

> **Live dashboard:** _(Tableau Public link goes here once published)_
> **Persona:** Sam & Priya — $1.2M budget, dual income, WFH 3 days, planning kids in ~3 years.
> **Headline number:** narrows ~700 candidate suburbs to a ranked top-5 in one view.

---

## What's in the box

| | |
|---|---|
| **Geographic scope** | 794 Greater Sydney SALs (bbox filter), 741 in the final fact table after dropping no-sales ghosts |
| **Price data** | NSW Valuer General — 731,718 residential sales over the last 5 years |
| **Demographics** | ABS Census 2021 General Community Profile at SAL level (NSW pack) |
| **Crime** | BOCSAR recorded crime by suburb — 12 most recent months summed |
| **Commute** | Haversine straight-line proxy to Sydney Town Hall × 1.5 min/km (v1 cut; GTFS scheduled times on v2 list) |

## Scoring

A weighted composite of four 0–100 pillar subscores:

```
composite = ( w_aff * affordability_norm
            + w_com * commute_norm
            + w_lif * lifestyle_norm
            + w_gro * growth_norm
            ) / (w_aff + w_com + w_lif + w_gro)
```

Defaults are **35% / 20% / 25% / 20%** (the Sam & Priya persona); the Tableau
dashboard exposes the four weights as sliders so anyone can re-weight live.

Each pillar is computed from a raw signal, clipped at the 1st and 99th
percentile to keep coastal outliers from squashing the rest of the
distribution, then min-max normalised. See [`docs/methodology.md`](docs/methodology.md)
for the full formulas, polarities, and caveats.

## Reproducing the pipeline

```bash
git clone https://github.com/tczhao/sydney-suburb-scorecard.git
cd sydney-suburb-scorecard
python3 -m venv .venv
source .venv/Scripts/activate          # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python etl/00_download_raw.py          # ~150 MB of public-only data
python etl/01_build_dim_suburb.py
python etl/02_load_vg_sales.py
python etl/03_load_census.py
python etl/04_load_crime.py
python etl/05_commute_proxy.py
python etl/06_build_fact.py            # writes tableau/suburb_scores.csv
```

Open `tableau/suburb_scores.csv` in Tableau Desktop Public Edition to
rebuild the dashboard (see Phase 4 in the project plan).

## Project structure

```
.
├── docs/                       # design docs
│   ├── persona.md
│   └── methodology.md
├── etl/                        # ordered pipeline scripts
│   ├── 00_download_raw.py
│   ├── 01_build_dim_suburb.py
│   ├── 02_load_vg_sales.py
│   ├── 03_load_census.py
│   ├── 04_load_crime.py
│   ├── 05_commute_proxy.py
│   └── 06_build_fact.py
├── tableau/
│   └── suburb_scores.csv       # 24 cols × 741 rows; Tableau input
├── data/raw/                   # gitignored; populated by 00_download_raw.py
├── sydney_scorecard.duckdb     # gitignored; built by the ETL
├── requirements.txt
└── README.md
```

## Known limitations (v1)

Documented in detail in [`docs/methodology.md`](docs/methodology.md). The
sharpest ones:

- Commute uses a straight-line proxy, not scheduled GTFS times. Ranks well, predicts poorly.
- House + unit medians are pooled, so unit-heavy suburbs look artificially cheap relative to a "house" budget.
- Bounding-box approach to Greater Sydney over-includes the Hawkesbury / Central Coast edge by a few suburbs.
- CBD-style suburbs (Sydney, Haymarket) have inflated `crime_per_1000` because of tiny residential populations vs high foot-traffic offence counts — known BOCSAR artifact.

## Data sources (all free, all direct download)

| Source | Use | URL |
|---|---|---|
| ABS ASGS Edition 3 SAL boundaries | Suburb shapes + centroids | https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3 |
| ABS Census 2021 GCP (SAL, NSW pack) | Population + medians | https://www.abs.gov.au/census/find-census-data/datapacks |
| NSW Valuer General Bulk Property Sales | Sale prices, 5yr CAGR | https://nswpropertysalesdata.com/ |
| BOCSAR Recorded crime by suburb | Crime per 1000 | https://data.nsw.gov.au/data/dataset/crime-by-offence-by-nsw-suburb |
