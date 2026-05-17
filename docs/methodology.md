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
| Commute | `−commute_minutes_cbd` (haversine to Town Hall × 1.5 min/km) | Higher = better (less time) | ABS SAL centroid + hardcoded Town Hall lat/lon |
| Lifestyle | Average of `z(−crime_per_1000)` (BOCSAR / Census G01 pop) and `z(median_hhd_inc_weekly)` (Census G02) | Higher = better | BOCSAR + ABS Census 2021 |
| Growth | 5-year CAGR of suburb median sale price (compares last 12mo window to the 4-5 years ago window) | Higher = better | NSW Valuer General bulk sales |

> **Note vs original design:** the lifestyle pillar was originally going to use Census G33 owner-occupier %. The 2021 G33 table is actually "Total Household Income by Composition", not tenure. The pillar uses median household income (Census G02) as an affluence proxy instead, paired with the BOCSAR crime rate. Owner-occupier ratio is on the v2 list.

## Normalisation
Each raw pillar value is min-max normalised across all in-scope suburbs:

```
x_norm = 100 * (x − min(x)) / (max(x) − min(x))
```

Computed *after* outlier clipping at the 1st and 99th percentile to keep one or two extreme suburbs (very expensive coastal, or very cheap fringe) from squashing the rest of the distribution.

## Geographic scope
- **Greater Sydney** filtered via a bounding box over ABS SAL centroids: latitude **−34.20 to −33.40**, longitude **150.50 to 151.45**. This is a small superset of the official GCCSA `1GSYD` region — the proper SAL→GCCSA correspondence file ABS publishes only goes to the Meshblock level, and the join wasn't worth the size penalty for v1. Yields **794 SALs**.
- Crime rates suppressed (NULL) for suburbs with Census 2021 total population <500 — the rate is too noisy when the denominator is small. Note: original design used the ABS SA2-level Estimated Resident Population (ERP); the v1 simplification uses Census G01 total persons as the denominator, which means the population is the 2021 count, not a 2024-25 ERP. Trade-off accepted for v1.
- Suburb centroids are computed as the **bounding-box midpoint** of each SAL polygon (not the geometric centroid). Fine for ranking-style commute proxies; not suitable for any analysis that needs the true population-weighted centroid.
- `fact_suburb_metrics` drops suburbs with no residential sales in the last 12 months (~53 ghosts, mostly nature reserves and industrial pockets). Final table has **741 suburbs**.

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
- **Commute is a straight-line proxy**, not a scheduled travel time. A suburb separated from the CBD by water or no rail line will be over-rated. The 1.5 min/km factor approximates door-to-door public-transit time on average but under-shoots in real terms (the proxy puts Penrith at 75 min; an actual train is ~70 min, but Bondi shows 9 min when the bus is closer to 25). Acceptable for *ranking*, not for absolute commute prediction.
- **Domain asking prices not included** — Valuer General sold prices are used everywhere. More rigorous (actual transactions) but slightly less timely.
- **Lifestyle composite is intentionally narrow** — only crime rate + median household income. School quality, walkability, green space, owner-occupier ratio are v2.
- **CBD-style suburbs (Sydney, Haymarket) have inflated crime/capita** because the residential population is tiny relative to foot-traffic-driven offence counts. They appear with the highest `crime_per_1000` despite not being unsafe for residents in any meaningful sense — a documented BOCSAR limitation, not a data error.
- **Bounding box leak** — the Greater Sydney bbox slightly over-includes at the northern edge (Gosford, on the Central Coast at lat −33.42, slipped in). Visible in any "highest crime" listing.
- **Suburbs with no recent sales are dropped** from `fact_suburb_metrics` (53 of 794). They can't be priced and therefore can't be scored on affordability or growth.
- **Property type mix** — medians are computed across houses + units combined. A unit-heavy suburb will look artificially "affordable" against a budget calibrated for a house. The default-weighted top-10 reflects this: it's dominated by unit suburbs in Western/SW Sydney (Lakemba, Wiley Park, Homebush West). Surfacing this trade-off is part of why the dashboard exposes weight sliders.
- **5-year CAGR window** — compares median price in the last 12 months against the median in the 4-to-5 years-ago window. Both windows require ≥3 sales; otherwise CAGR is NULL (~27 suburbs are NULL).

## Next steps (v2)
- Replace haversine commute with **GTFS-scheduled travel time** to Town Hall and Parramatta (dual-anchor CBD).
- Add **Domain Developer API** asking-price as a forward-looking signal vs the lagging Valuer General sold prices.
- Cross-validate medians against the Kaggle Sydney House Prices dataset (https://www.kaggle.com/datasets/alexlau203/sydney-house-prices).
- Add school catchment quality (NAPLAN / My School API) once the persona is in family-formation phase.
- **Split house vs unit medians** so the affordability pillar is type-aware — the single most impactful v2 change.
- Replace the bbox filter with a real SAL→GCCSA join via the ABS Meshblock allocation file. Removes the Central Coast bleed.
- Use ABS SA2-level **2024-25 ERP** instead of 2021 Census G01 for the crime denominator — picks up post-pandemic population shifts.
- Add **owner-occupier %** to the lifestyle pillar (Census G37 / G38, not G33 as originally assumed).
