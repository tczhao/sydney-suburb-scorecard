# Building the dashboard in Tableau Desktop Public Edition

The `sydney_scorecard.twb` workbook ships pre-wired with:

- The CSV data source (`suburb_scores.csv` in this folder)
- Geographic roles assigned to `centroid_lat` / `centroid_lon`
- **4 parameters** (`w_aff`, `w_com`, `w_lif`, `w_gro`) — float, range 0–1, step 0.05, defaults 0.35/0.20/0.25/0.20
- **4 calculated fields**:
  - `Weight Sum`
  - `Composite Score`
  - `Rank`
  - `Under Budget Flag` (median_sale_price_12m ≤ 1200000)

You only have to build two worksheets and a dashboard. ~15 minutes.

## Sanity check after opening
1. Open `sydney_scorecard.twb` in Tableau Desktop Public Edition.
2. If the CSV path doesn't resolve, in Data pane → right-click `suburb_scores` → Edit Connection → point to `tableau/suburb_scores.csv`.
3. Confirm the 4 parameters appear in the Data pane (bottom-left), and the 4 calculated fields show up as measures.
4. If the connection works but parameters don't show, the XML was rejected — fall back to building from scratch using the formulas below, or run the Streamlit version instead.

## Sheet 1 — Map

1. **New Sheet**, rename to `Map`.
2. Drag `centroid_lon` to **Columns**, `centroid_lat` to **Rows**. (Both should already be set as geographic.)
3. Change the mark type (top of Marks card) to **Circle**.
4. Drag `suburb_name` to **Detail**.
5. Drag `Composite Score` to **Color**. Pick a diverging palette (Red-Blue Diverging) and reverse it so high = blue.
6. Drag `Composite Score` to **Size**.
7. Drag the four weight parameters into the Tooltip card so they show on hover. Also add `median_sale_price_12m`, `commute_minutes_cbd`, `crime_per_1000`, `price_5yr_cagr`.
8. Right-click each parameter in the Data pane → **Show Parameter** — gives you the slider controls in the right-hand panel.
9. (Optional) Add `Under Budget Flag = True` to the **Filters** card so off-budget suburbs disappear.

## Sheet 2 — Top suburbs

1. **New Sheet**, rename to `Top Suburbs`.
2. Drag `Rank` to **Filters**, set to "Top by field" → Top 20 by `Composite Score` (descending).
3. Drag `Rank` to **Rows** (discrete) — should already be discrete after the filter.
4. Drag `suburb_name` to **Rows** (after Rank).
5. Drag `Measure Names` to **Columns**, `Measure Values` to **Text** on the Marks card.
6. In the Measure Values card, keep only: `Composite Score`, `affordability_norm`, `commute_norm`, `lifestyle_norm`, `growth_norm`, `median_sale_price_12m`, `commute_minutes_cbd`.
7. Apply a stepped color background to each `*_norm` column (right-click each measure → Format → background colour).

## Dashboard

1. **New Dashboard**, set size to 1366×768 (or "Automatic").
2. Drag the `Map` sheet onto the canvas (top-half).
3. Drag the `Top Suburbs` sheet underneath.
4. From the right panel, drag each of the four weight parameter controls into a vertical container at the top.
5. Add a Text object as the title: "Sam & Priya — Sydney suburb scorecard".
6. (Optional) Add a Web Page object pointing to your methodology.md GitHub URL as a "Read methodology" tab.

## Publishing

`File → Save to Tableau Public As…` → sign in → name "Sydney Suburb Scorecard" → Save. Tableau hands you a public URL — drop that into `README.md` (replace the placeholder).

## If the .twb pre-wiring failed to load

Open Tableau Desktop Public Edition fresh, connect to `tableau/suburb_scores.csv`, then build the parameters and calculated fields by hand. Formulas:

```
w_aff, w_com, w_lif, w_gro    -- Float, range [0, 1], step 0.05
                                 defaults 0.35, 0.20, 0.25, 0.20

Weight Sum
    [w_aff] + [w_com] + [w_lif] + [w_gro]

Composite Score
    (  [w_aff] * AVG([affordability_norm])
     + [w_com] * AVG([commute_norm])
     + [w_lif] * AVG([lifestyle_norm])
     + [w_gro] * AVG([growth_norm])
    ) / ([w_aff] + [w_com] + [w_lif] + [w_gro])

Rank
    RANK([Composite Score], 'desc')

Under Budget Flag
    [median_sale_price_12m] <= 1200000
```

Then follow Sheet 1 / Sheet 2 / Dashboard steps above. ~30 minutes total.
