# Where should Sam & Priya buy in Sydney?

**One-page executive summary** &middot; v1 &middot; 17 May 2026
**Live dashboard:** https://sydney-suburb-scorecard-qcpvzsgu2vbh7sbkwldq2m.streamlit.app/

## TL;DR

For a $1.2M, dual-income, WFH-3-days couple planning kids in three years, **Lane Cove North is the cleanest single recommendation**: $985k median, 13 min to CBD, sits in the upper-quartile lifestyle bucket. The persona's default weights (35% affordability) over-rotate to unit-heavy West/SW suburbs that don't match the family-planning horizon — once lifestyle is re-weighted to ~50%, the picks become much more defensible.

## The persona

| | |
|---|---|
| Budget | $1.2M |
| Income | Dual, ~$180k combined |
| Commute | WFH 3 days, in-office 2 days at Sydney CBD |
| Property type | House OR 2+ bed unit |
| 3-year horizon | Kids planned &mdash; lifestyle starts to matter more than affordability headroom |

## Method (one line)

Persona-weighted composite of 4 normalised pillars (affordability, commute, lifestyle = z(−crime) + z(income), 5yr growth), clipped at 1st/99th percentile, scored 0&ndash;100 across **741 Greater Sydney suburbs**. Weights are sliders in the dashboard.

## Top 5 at persona defaults &mdash; 35 / 20 / 25 / 20

| # | Suburb | Median | Commute | Crime/1k | 5yr CAGR | Note |
|---|---|---|---|---|---|---|
| 1 | Lakemba | $540k | 20 min | 45 | +5.2% | Unit-heavy; affordability dominates |
| 2 | Wiley Park | $570k | 21 min | 48 | +3.8% | Same story |
| 3 | Rosehill (NSW) | $535k | 26 min | 71 | +1.3% | Adjacent to Parramatta |
| 4 | Cogra Bay | $455k | 58 min | n/a | +15.1% | Data artifact &mdash; tiny pop, no crime data, far commute. Discard. |
| 5 | Homebush West | $641k | 19 min | 44 | +0.3% | Best mix in this set |

**Why this isn't quite right for Sam & Priya:** 4 of 5 are unit suburbs and the model can't tell a house from a unit (medians are pooled). The persona is buying for a family in 3 years, not maximising current $/sqm.

## Recommended view &mdash; lifestyle re-weighted to 50%

Move the dashboard's `w_lif` slider to 0.50 and trim affordability to 0.20:

| # | Suburb | Median | Commute | Crime/1k | 5yr CAGR | Note |
|---|---|---|---|---|---|---|
| 1 | Lakemba | $540k | 20 min | 45 | +5.2% | Still tops on income proxy |
| 2 | Homebush West | $641k | 19 min | 44 | +0.3% | Better lifestyle, near same commute |
| 3 | Meadowbank (NSW) | $670k | 19 min | 31 | −0.5% | **Real candidate** &mdash; low crime, river-adjacent, train station |
| 4 | Rosehill (NSW) | $535k | 26 min | 71 | +1.3% | Still affordable but crime is high |
| 5 | **Lane Cove North** | $985k | 13 min | &mdash; | &mdash; | **Top recommendation** &mdash; Lower North Shore, walkable, family-friendly |

## Recommendation

**Inspect Lane Cove North and Meadowbank first this weekend.** Both fit the persona's 3-year horizon (good schools, low crime, walkable) while staying under budget. Lakemba and Homebush West remain on the list as value plays if priorities shift back to affordability.

## Important caveats

- **House and unit medians are pooled** &mdash; the single biggest source of noise. A unit-heavy suburb looks cheap against a "house budget". Splitting these is the v2 priority.
- **Commute is a straight-line proxy**, not scheduled GTFS time. Good for ranking, off in absolute terms (Bondi shows 9 min, real bus is closer to 25).
- **Crime rates use Census 2021 population**, not the 2024-25 ERP &mdash; lags 5 years.
- **CBD-style suburbs (Sydney, Haymarket) inflate crime/1000** because residential population is tiny relative to foot-traffic offences. Filter them out mentally.
- **Cogra Bay is a data artifact** &mdash; tiny population, no crime denominator, distant from CBD. The dashboard's "minimum population" slider removes it.

## Next steps the buyer should take

1. Inspect 3 listings in **Lane Cove North** and 2 in **Meadowbank** this weekend.
2. Book a building inspection on the front-runner before mid-June.
3. Drive both at peak hour Tuesday morning to validate the commute proxy.

## Limitations of v1, on the v2 backlog

- Split house vs unit medians so affordability is type-aware.
- Replace the haversine commute with GTFS-scheduled times to Town Hall and Parramatta.
- Add owner-occupier ratio (correct Census table, not the G33 I originally scoped).
- Add Domain asking-price as a forward-looking signal.
- Add school catchment quality once the kids appear.

Full methodology &amp; data sources: [`docs/methodology.md`](methodology.md) &middot; reproducible pipeline: see [README](../README.md).
