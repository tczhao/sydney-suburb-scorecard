"""Sydney Suburb Scorecard - Streamlit dashboard.

Run locally:
    streamlit run streamlit_app.py

Deploy: push to GitHub, then connect the repo at https://share.streamlit.io.
Streamlit Community Cloud will pick up requirements.txt automatically and
expose this file at https://<your-username>-<repo-name>.streamlit.app.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

CSV_PATH = Path(__file__).parent / "tableau" / "suburb_scores.csv"
PERSONA_BUDGET = 1_200_000


# ---------- Data ----------------------------------------------------------------


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(CSV_PATH)


def compute_composite(
    df: pd.DataFrame, w_aff: float, w_com: float, w_lif: float, w_gro: float
) -> pd.DataFrame:
    weights = max(w_aff + w_com + w_lif + w_gro, 1e-6)
    out = df.copy()
    out["composite"] = (
        w_aff * out["affordability_norm"].fillna(0)
        + w_com * out["commute_norm"].fillna(0)
        + w_lif * out["lifestyle_norm"].fillna(0)
        + w_gro * out["growth_norm"].fillna(0)
    ) / weights
    out["rank"] = out["composite"].rank(method="min", ascending=False).astype(int)
    return out


# ---------- Page setup ----------------------------------------------------------

st.set_page_config(
    page_title="Sydney Suburb Scorecard",
    page_icon=":house:",
    layout="wide",
)

st.title("Sydney Suburb Investment Scorecard")
st.markdown(
    "Persona: **Sam & Priya** &mdash; $1.2M budget, dual income, WFH 3 days, "
    "planning kids in &sim;3 years. Drag the sliders to re-weight; the map and "
    "table update live."
)

df_raw = load_data()


# ---------- Sidebar -------------------------------------------------------------

st.sidebar.header("Persona weights")
st.sidebar.caption("Defaults match Sam & Priya. Higher = matters more.")
w_aff = st.sidebar.slider("Affordability", 0.0, 1.0, 0.35, 0.05)
w_com = st.sidebar.slider("Commute to CBD", 0.0, 1.0, 0.20, 0.05)
w_lif = st.sidebar.slider("Lifestyle (low crime + income)", 0.0, 1.0, 0.25, 0.05)
w_gro = st.sidebar.slider("5yr price growth", 0.0, 1.0, 0.20, 0.05)

st.sidebar.markdown("---")
under_budget = st.sidebar.checkbox(
    f"Only show suburbs with median &le; ${PERSONA_BUDGET:,.0f}",
    value=True,
)
min_pop = st.sidebar.slider(
    "Minimum population (suppress tiny suburbs)",
    0,
    5000,
    500,
    100,
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Built from public NSW Valuer General, ABS Census 2021, and BOCSAR data. "
    "[GitHub](https://github.com/tczhao/sydney-suburb-scorecard) - "
    "[Methodology](https://github.com/tczhao/sydney-suburb-scorecard/blob/main/docs/methodology.md)"
)


# ---------- Compute -------------------------------------------------------------

df = compute_composite(df_raw, w_aff, w_com, w_lif, w_gro)

if under_budget:
    df = df[df["median_sale_price_12m"] <= PERSONA_BUDGET]
df = df[df["total_pop"] >= min_pop]


# ---------- KPI strip -----------------------------------------------------------

top5 = df.nlargest(5, "composite")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Suburbs in scope", f"{len(df):,}")
col2.metric(
    "Top suburb",
    top5.iloc[0]["suburb_name"] if not top5.empty else "&mdash;",
    f"score {top5.iloc[0]['composite']:.1f}" if not top5.empty else "",
)
col3.metric(
    "Median $ of top 5",
    f"${top5['median_sale_price_12m'].median():,.0f}" if not top5.empty else "&mdash;",
)
col4.metric(
    "Median commute (top 5)",
    f"{top5['commute_minutes_cbd'].median():.0f} min" if not top5.empty else "&mdash;",
)


# ---------- Map -----------------------------------------------------------------

st.subheader("Composite score across Sydney")

map_df = df.dropna(subset=["centroid_lat", "centroid_lon", "composite"])

fig = px.scatter_mapbox(
    map_df,
    lat="centroid_lat",
    lon="centroid_lon",
    color="composite",
    size="composite",
    size_max=18,
    hover_name="suburb_name",
    hover_data={
        "composite": ":.1f",
        "rank": True,
        "median_sale_price_12m": ":$,.0f",
        "commute_minutes_cbd": ":.1f",
        "crime_per_1000": ":.1f",
        "price_5yr_cagr": ":.1%",
        "centroid_lat": False,
        "centroid_lon": False,
    },
    color_continuous_scale="Viridis",
    zoom=9,
    center={"lat": -33.87, "lon": 151.0},
    mapbox_style="open-street-map",
)
fig.update_layout(
    height=600,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    coloraxis_colorbar={"title": "Composite"},
)
st.plotly_chart(fig, use_container_width=True)


# ---------- Top suburbs table ---------------------------------------------------

st.subheader("Top 20 suburbs by composite score")

table_cols = [
    "rank",
    "suburb_name",
    "composite",
    "affordability_norm",
    "commute_norm",
    "lifestyle_norm",
    "growth_norm",
    "median_sale_price_12m",
    "commute_minutes_cbd",
    "crime_per_1000",
    "price_5yr_cagr",
]
top20 = df.nlargest(20, "composite")[table_cols].copy()

st.dataframe(
    top20,
    column_config={
        "rank": st.column_config.NumberColumn("Rank", width="small"),
        "suburb_name": "Suburb",
        "composite": st.column_config.ProgressColumn(
            "Composite", min_value=0, max_value=100, format="%.1f"
        ),
        "affordability_norm": st.column_config.ProgressColumn(
            "Afford.", min_value=0, max_value=100, format="%.0f"
        ),
        "commute_norm": st.column_config.ProgressColumn(
            "Commute", min_value=0, max_value=100, format="%.0f"
        ),
        "lifestyle_norm": st.column_config.ProgressColumn(
            "Lifestyle", min_value=0, max_value=100, format="%.0f"
        ),
        "growth_norm": st.column_config.ProgressColumn(
            "Growth", min_value=0, max_value=100, format="%.0f"
        ),
        "median_sale_price_12m": st.column_config.NumberColumn(
            "Median price (12mo)", format="$%d"
        ),
        "commute_minutes_cbd": st.column_config.NumberColumn(
            "Commute (min)", format="%.1f"
        ),
        "crime_per_1000": st.column_config.NumberColumn(
            "Crime / 1k", format="%.1f"
        ),
        "price_5yr_cagr": st.column_config.NumberColumn(
            "5yr CAGR", format="%.1f%%"
        ),
    },
    hide_index=True,
    use_container_width=True,
    height=720,
)


# ---------- Caveats expander ----------------------------------------------------

with st.expander("Methodology & known limitations"):
    st.markdown(
        """
- **Commute** is a haversine distance to Sydney Town Hall &times; 1.5 min/km, not scheduled GTFS times. Good for ranking; over-rates suburbs separated by water with no rail link.
- **Crime denominator** is Census 2021 total population (not the 2024-25 ERP). CBD-style suburbs (Sydney, Haymarket) appear with inflated `crime_per_1000` because of tiny residential populations against high foot-traffic offence counts &mdash; a known BOCSAR artifact, not real danger.
- **House and unit medians are pooled** &mdash; unit-heavy suburbs look artificially cheap against a budget calibrated for a house. At default weights the top picks skew to Western/SW Sydney unit suburbs precisely because of this.
- **Geographic scope** uses a bounding-box approximation of Greater Sydney; a handful of Hawkesbury / Central Coast edge suburbs leak in (Gosford is visible in the high-crime list).
- **741 suburbs** in the fact table (794 in scope, 53 dropped for no recent sales).
- Full design and v2 backlog: [docs/methodology.md](https://github.com/tczhao/sydney-suburb-scorecard/blob/main/docs/methodology.md)
"""
    )
