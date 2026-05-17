# Methodology — Sydney Suburb Investment Scorecard

## Approach
For every Greater Sydney suburb, compute a single composite score in [0, 100] as a weighted sum of four normalised pillar subscores. Weights default to the Sam & Priya persona (see `persona.md`) but are user-adjustable in the Tableau dashboard.

```
composite_score(suburb) =
  ( w_aff * affordability_norm
  + w_com * commute_norm
  + w_lif * lifestyle_norm
  + w_gro * growth_norm
  ) / (w_aff + w_com + w_lif + w_gro)
```

Division by the sum of weights keeps the score on a 0–100 scale even if the user moves sliders so they no longer total 1.

## Pillar definitions

| Pillar | Raw input | Polarity | Source |
|---|---|---|---|
| Affordability | `(persona_budget − median_sale_price_12m) / median_sale_price_12m` | Higher = better (more headroom under budget) | NSW Valuer General bulk sales |
| Commute | `−commute_minutes_cbd` | Higher = better (less time) | Haversine distance × 1.5 min/km proxy to Town Hall |
| Lifestyle | Composite of `−crime_per_1000` (BOCSAR) + `+pct_owner_occupier` (Census G33), z-scored and averaged | Higher = better | BOCSAR + ABS Census 2021 |
| Growth | 5-year CAGR of suburb median sale price | Higher = better | NSW Valuer General bulk sales |

## Normalisation
Each raw pillar value is min-max normalised across all in-scope suburbs:

```
x_norm = 100 * (x − min(x)) / (max(x) − min(x))
```

Computed *after* outlier clipping at the 1st and 99th percentile to keep one or two extreme suburbs (very expensive coastal, or very cheap fringe) from squashing the rest of the distribution.

## Geographic scope
- **Greater Sydney** = ABS GCCSA code `1GSYD` (~700 suburbs / SAL units).
- Crime rates suppressed and treated as NULL for suburbs with ABS Estimated Resident Population <500.
- Suburb centroids derived from the ABS SAL boundary file; suburbs with missing centroids fall back to LGA centroid (flagged in the data).

## Data sources
| Source | URL | Use |
|---|---|---|
| NSW Valuer General Bulk Property Sales | https://nswpropertysalesdata.com/ (CSV mirror) | Sales prices, 5yr CAGR |
| ABS Census 2021 General Community Profile (SA2) | https://www.abs.gov.au/census/find-census-data/datapacks | Income, tenure, WFH, demographics |
| BOCSAR Recorded Crime by Suburb | https://data.nsw.gov.au/ | Crime per 1000 (12mo) |
| ABS Regional Population | https://www.abs.gov.au/statistics/people/population | ERP denominator for crime rate |
| TfNSW GTFS bundle | https://opendata.transport.nsw.gov.au/ | Station coordinates only (commute is haversine proxy) |
| ABS ASGS 2021 Edition 3 correspondences | https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3 | SAL ↔ SA2 ↔ LGA crosswalk + centroids |

## Caveats (v1)
- **Commute is a straight-line proxy**, not a scheduled travel time. A suburb separated from the CBD by water or no rail line will be over-rated. Acceptable for ranking, not for absolute commute prediction.
- **Domain asking prices not included** — Valuer General sold prices are used everywhere. This is more rigorous (actual transactions) but slightly less timely.
- **Lifestyle composite is intentionally narrow** — only crime + owner-occupier %. School quality, walkability, green space are v2.
- **Suppressed crime suburbs** are excluded from the lifestyle subscore; their composite uses only the remaining 3 pillars (re-weighted on the fly).
- **Property type mix** — medians are computed across houses + units combined. A suburb with mostly units will look artificially "affordable" against a budget set for a house.

## Next steps (v2)
- Replace haversine commute with GTFS-scheduled travel time to Town Hall and Parramatta (dual-anchor CBD).
- Add Domain Developer API asking-price as a forward-looking signal vs Valuer General lagging.
- Cross-validate medians against Kaggle Sydney House Prices dataset (https://www.kaggle.com/datasets/alexlau203/sydney-house-prices).
- Add school catchment quality (NAPLAN / My School API) once the persona is in family-formation phase.
- Split house vs unit medians so the affordability pillar is type-aware.
