"""
Statistische analyse-pagina voor vertragingen (Jelle van Wees).
Bevat uitleg, robuuste statistiek en visualisaties per hypothese.
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from typing import Dict, Any, List

from flight_data import load_airline_lookup, load_airport_lookup, load_flights

st.set_page_config(page_title="Statistische Analyse — Flight Delays", layout="wide", page_icon="📈")
st.title("Statistische Analyse — Flight Delay Dashboard")
st.caption("Academische onderbouwing van de hypotheses met statistiek en visualisaties (Connectivity & Mobility).")


# ------------------------------
# Helpers
# ------------------------------
def apply_filters(df: pd.DataFrame, months, airlines, origins, destinations) -> pd.DataFrame:
    """Filter dataframe op gekozen maanden, airlines, vertrek- en bestemmingsluchthavens."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df
    if months:
        out = out[out["MONTH"].isin(months)]
    if airlines:
        out = out[out["AIRLINE"].isin(airlines)]
    if origins:
        out = out[out["ORIGIN_AIRPORT"].isin(origins)]
    if destinations:
        out = out[out["DESTINATION_AIRPORT"].isin(destinations)]
    return out


def winsorize_delays(df: pd.DataFrame, pct: float) -> pd.DataFrame:
    """Clip extreme vertragingen voor robuustheid (percentiel)."""
    if df.empty or pct <= 0:
        return df
    df = df.copy()
    for col in ["ARRIVAL_DELAY", "DEPARTURE_DELAY"]:
        lower = df[col].quantile(pct / 100)
        upper = df[col].quantile(1 - pct / 100)
        df[col] = df[col].clip(lower, upper)
    return df


def hourly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Samenvatting per vertrekuur, met weer-aandeel."""
    if df.empty:
        return pd.DataFrame(columns=["dep_hour", "mean_arr_delay", "median_arr_delay", "weather_share_pct", "flights"])
    hourly = (
        df.groupby("dep_hour")
        .agg(
            mean_arr_delay=("ARRIVAL_DELAY", "mean"),
            median_arr_delay=("ARRIVAL_DELAY", "median"),
            weather_share=("has_weather_delay", "mean"),
            flights=("ARRIVAL_DELAY", "size"),
        )
        .reset_index()
        .sort_values("dep_hour")
    )
    hourly["weather_share_pct"] = hourly["weather_share"] * 100
    return hourly


def linear_trend_dep_hour(df: pd.DataFrame) -> Dict[str, Any]:
    """Ruwe trend van aankomstvertraging vs vertrekuur."""
    if df.empty or df["dep_hour"].nunique() < 2:
        return {"slope": None, "r2": None}
    x = df["dep_hour"].to_numpy()
    y = df["ARRIVAL_DELAY"].to_numpy()
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2:
        return {"slope": None, "r2": None}
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    ss_res = np.sum((y - y_pred) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else None
    return {"slope": slope, "r2": r2}


def controlled_trend(df: pd.DataFrame) -> Dict[str, Any]:
    """Trend gecorrigeerd voor maand en weekdag (residuen)."""
    needed = {"dep_hour", "ARRIVAL_DELAY", "MONTH", "DAY_OF_WEEK"}
    if df.empty or df["dep_hour"].nunique() < 2 or not needed.issubset(df.columns):
        return {"slope": None, "r2": None}
    arr = df["ARRIVAL_DELAY"]
    arr_resid = arr - arr.groupby([df["MONTH"], df["DAY_OF_WEEK"]]).transform("mean")
    x = df["dep_hour"].to_numpy()
    y = arr_resid.to_numpy()
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2:
        return {"slope": None, "r2": None}
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    ss_res = np.sum((y - y_pred) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else None
    return {"slope": slope, "r2": r2}


def anova_dep_hour(df: pd.DataFrame) -> Dict[str, Any]:
    """One-way ANOVA over vertrekuur."""
    if df.empty:
        return {"f_stat": None, "p_value": None, "effect_size": None}
    grouped = df.groupby("dep_hour")["ARRIVAL_DELAY"]
    counts = grouped.size()
    if len(counts) < 2:
        return {"f_stat": None, "p_value": None, "effect_size": None}
    means = grouped.mean()
    overall_mean = df["ARRIVAL_DELAY"].mean()
    ss_between = ((means - overall_mean) ** 2 * counts).sum()
    vars_ = grouped.var()
    ss_within = (vars_ * (counts - 1)).sum()
    df_between = len(means) - 1
    df_within = len(df) - len(means)
    if df_within <= 0 or ss_within <= 0:
        return {"f_stat": None, "p_value": None, "effect_size": None}
    f_stat = (ss_between / df_between) / (ss_within / df_within)
    effect_size = ss_between / (ss_between + ss_within) if (ss_between + ss_within) > 0 else None
    p_value = None
    try:
        from scipy.stats import f as f_dist

        p_value = float(f_dist.sf(f_stat, df_between, df_within))
    except Exception:
        p_value = None
    return {"f_stat": f_stat, "p_value": p_value, "effect_size": effect_size}


def safe_corr(df: pd.DataFrame, col_x: str, col_y: str) -> float | None:
    """Veilige Pearson correlatie."""
    if df.empty or col_x not in df or col_y not in df:
        return None
    corr = df[[col_x, col_y]].corr().iloc[0, 1]
    return None if np.isnan(corr) else corr


def hub_flag(df: pd.DataFrame, quantile: float = 0.8) -> pd.DataFrame:
    """Markeer hubs (top quantile volume per ORIGIN_AIRPORT)."""
    if df.empty or "ORIGIN_AIRPORT" not in df:
        return df
    counts = df["ORIGIN_AIRPORT"].value_counts()
    if counts.empty:
        return df
    threshold = counts.quantile(quantile)
    hubs = counts[counts >= threshold].index
    df = df.copy()
    df["is_hub"] = df["ORIGIN_AIRPORT"].isin(hubs)
    return df


def build_scatter_dep_hour(df: pd.DataFrame):
    if df.empty:
        return None
    blue = "#2f4b7c"
    orange = "#f28e2c"
    zero_rule = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#cccccc", strokeDash=[2, 2]).encode(y="y:Q")
    return (
        zero_rule
        + alt.Chart(df)
        .mark_circle(opacity=0.25, color=blue)
        .encode(
            x=alt.X("dep_hour:O", title="Vertrekuur (0–23)"),
            y=alt.Y("ARRIVAL_DELAY:Q", title="Aankomstvertraging (min)"),
            tooltip=["dep_hour", alt.Tooltip("ARRIVAL_DELAY", title="Aankomstvertraging", format=".1f")],
        )
        .transform_regression("dep_hour", "ARRIVAL_DELAY")
        .mark_line(color=orange, strokeDash=[6, 3])
        .properties(title="Scatter: Vertrekuur vs aankomstvertraging")
    )


def build_scatter_dep_arr(df: pd.DataFrame):
    if df.empty:
        return None
    blue = "#2f4b7c"
    orange = "#f28e2c"
    zero_rule = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#cccccc", strokeDash=[2, 2]).encode(y="y:Q")
    # sample om performance te houden
    scatter = (
        alt.Chart(df.sample(min(len(df), 5000), random_state=1))
        .mark_circle(opacity=0.25, color=blue)
        .encode(
            x=alt.X("DEPARTURE_DELAY:Q", title="Vertrekvertraging (min)"),
            y=alt.Y("ARRIVAL_DELAY:Q", title="Aankomstvertraging (min)"),
            tooltip=[
                alt.Tooltip("DEPARTURE_DELAY", title="Vertrekvertraging", format=".1f"),
                alt.Tooltip("ARRIVAL_DELAY", title="Aankomstvertraging", format=".1f"),
            ],
        )
    )
    line = scatter.transform_regression("DEPARTURE_DELAY", "ARRIVAL_DELAY").mark_line(color=orange, strokeDash=[6, 3])
    return (zero_rule + scatter + line).properties(title="Scatter: Vertrekvertraging vs aankomstvertraging")


def build_hub_bar(df: pd.DataFrame):
    if df.empty or "is_hub" not in df:
        return None
    blue = "#2f4b7c"
    orange = "#f28e2c"
    agg = (
        df.groupby("is_hub")["ARRIVAL_DELAY"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_delay"})
    )
    agg["type"] = agg["is_hub"].map({True: "Hubs (top 20% volume)", False: "Niet-hubs"})
    agg = agg.sort_values("avg_delay", ascending=False)
    return (
        alt.Chart(agg)
        .mark_bar(color=orange)
        .encode(
            x=alt.X("type:N", title="Luchthaven-type"),
            y=alt.Y("avg_delay:Q", title="Gem. aankomstvertraging (min)"),
            tooltip=[
                alt.Tooltip("type:N", title="Type"),
                alt.Tooltip("avg_delay:Q", format=".1f", title="Gem. aankomstvertraging"),
                alt.Tooltip("count:Q", format=",.0f", title="# vluchten"),
            ],
        )
        .properties(title="Hubs vs niet-hubs (gem. aankomstvertraging)")
    )


def format_filters(months, airlines, origins, destinations, airline_lookup, airport_lookup) -> str:
    """Maak een leesbare samenvatting van actieve filters."""
    parts: List[str] = []
    parts.append(f"Maanden: {'alle' if not months else ', '.join(map(str, months))}")
    if airlines:
        names = [f"{a} ({airline_lookup.get(a, a)})" for a in airlines]
        parts.append("Airlines: " + ", ".join(names))
    else:
        parts.append("Airlines: alle")
    if origins:
        names = [airport_lookup.get(o, o) for o in origins]
        parts.append("Vertrek: " + ", ".join(names))
    else:
        parts.append("Vertrek: alle")
    if destinations:
        names = [airport_lookup.get(d, d) for d in destinations]
        parts.append("Bestemming: " + ", ".join(names))
    else:
        parts.append("Bestemming: alle")
    return " | ".join(parts)


# ------------------------------
# Sidebar instellingen
# ------------------------------
with st.sidebar:
    st.header("Instellingen")
    row_limit = st.number_input(
        "Rijen laden (flights.csv)",
        min_value=50000,
        max_value=1000000,
        value=100000,
        step=50000,
        help="Minder rijen = snellere interactie; meer rijen = nauwkeuriger schattingen.",
    )
    trim_pct = st.slider("Winsorisatie (p%)", 0, 10, 1, help="Clip p en 100-p percentiel van vertragingen om uitschieters te temperen.")

df_raw = load_flights(int(row_limit))
airline_lookup = load_airline_lookup()
airport_lookup = load_airport_lookup()

st.info(
    "Dataset: flights.csv (VS, 2015) met airlines.csv en airports.csv voor labels. "
    "Cleaning: geannuleerde/omgeleide vluchten verwijderd, numerieke velden gecorrigeerd, afgeleiden toegevoegd (dep_hour, is_late_15, has_weather_delay)."
)

month_options = sorted(df_raw["MONTH"].dropna().unique().tolist()) if not df_raw.empty else []
airline_options = sorted(df_raw["AIRLINE"].dropna().unique().tolist()) if not df_raw.empty else []
origin_options = sorted(df_raw["ORIGIN_AIRPORT"].dropna().unique().tolist()) if not df_raw.empty else []
dest_options = sorted(df_raw["DESTINATION_AIRPORT"].dropna().unique().tolist()) if not df_raw.empty else []

default_state = {
    "months": month_options,
    "airlines": [],
    "origins": [],
    "destinations": [],
}

with st.sidebar:
    st.markdown("### Filters")
    if st.button("🔄 Reset filters", type="secondary"):
        for k, v in default_state.items():
            st.session_state[k] = v
        st.rerun()

    months = st.multiselect("Maanden", options=month_options, default=st.session_state.get("months", month_options), key="months")
    airlines = st.multiselect(
        "Airlines",
        options=airline_options,
        default=st.session_state.get("airlines", []),
        format_func=lambda x: f"{x} — {airline_lookup.get(x, x)}",
        key="airlines",
    )
    origins = st.multiselect("Vertrekluchthavens", options=origin_options, default=st.session_state.get("origins", []), format_func=lambda x: airport_lookup.get(x, x), key="origins")
    destinations = st.multiselect("Bestemmingen", options=dest_options, default=st.session_state.get("destinations", []), format_func=lambda x: airport_lookup.get(x, x), key="destinations")
    st.caption("Filters beïnvloeden alle statistieken en visualisaties op deze pagina.")

# ------------------------------
# Data filtering & cleaning
# ------------------------------
if df_raw.empty:
    st.error("Kon flights.csv niet laden of er zijn geen rijen beschikbaar.")
    st.stop()

filtered_pre = apply_filters(df_raw, months, airlines, origins, destinations)
filtered = winsorize_delays(filtered_pre, trim_pct)
filtered = hub_flag(filtered, quantile=0.8)
hourly = hourly_summary(filtered)
trend_stats = linear_trend_dep_hour(filtered)
ctrl_stats = controlled_trend(filtered)
anova_stats = anova_dep_hour(filtered)
corr_dep_arr = safe_corr(filtered, "DEPARTURE_DELAY", "ARRIVAL_DELAY")

st.markdown("### Introductie")
st.markdown(
    "Deze pagina toetst de hypotheses met regressie, ANOVA en correlatie. "
    "Alle cijfers zijn gebaseerd op de huidige filters en na cleaning (geen geannuleerde/omgeleide vluchten, optionele winsorisatie)."
)
st.info(
    "Cleaning: geannuleerde/omgeleide vluchten verwijderd; numerieke velden gecorrigeerd; optionele winsorisatie van vertragingen; hubs = top 20% drukste vertrekvelden in de gefilterde data."
)
st.caption(f"Actieve filters: {format_filters(months, airlines, origins, destinations, airline_lookup, airport_lookup)}")

with st.expander("📚 Theorie (kort)"):
    st.markdown(
        """
        - **Lineaire regressie**: slope = toename vertraging per uur later vertrek; R² = aandeel verklaarde variantie.
        - **Gecorrigeerde trend**: regressie op residuen na controle voor maand en weekdag (scheidt seizoen/dagpatroon uit).
        - **ANOVA (one-way)**: toetst of gemiddelden per vertrekuur verschillen; p < 0,05 duidt op significant verschil.
        - **Correlatie (Pearson r)**: sterkte/richting tussen vertrek- en aankomstvertraging; r → 1 = sterke positieve samenhang.
        """
    )

if filtered.empty:
    st.warning("Geen data over na filters. Verlaag drempels of selecteer meer maanden/airlines.")
    st.stop()

# Cleaning/traceerbaarheid
with st.container(border=True):
    st.markdown("#### Data cleaning en traceerbaarheid")
    col_clean1, col_clean2 = st.columns(2)
    with col_clean1:
        st.markdown(
            """
            **Stappen**
            - Filter: verwijder geannuleerde/omgeleide vluchten; pas gekozen filters toe.
            - Winsorisatie: clip vertragingen op p en 100-p om uitschieters te temperen.
            - Afleidingen: `dep_hour`, `is_late_15`, `has_weather_delay`; hubs = top 20% volume.
            """
        )
        st.caption("Motivatie: robuuste statistiek, minder invloed van extreme waarden, transparante definities.")
    with col_clean2:
        before_rows = len(filtered_pre)
        after_rows = len(filtered)
        miss_arr = filtered_pre["ARRIVAL_DELAY"].isnull().mean() * 100 if len(filtered_pre) else 0
        miss_dep = filtered_pre["DEPARTURE_DELAY"].isnull().mean() * 100 if len(filtered_pre) else 0
        st.metric("Rijen na filters", f"{before_rows:,}")
        st.metric("Rijen na winsorisatie", f"{after_rows:,}")
        st.caption(f"Missend vóór winsorisatie: ARRIVAL_DELAY {miss_arr:.2f}%, DEPARTURE_DELAY {miss_dep:.2f}%")
    st.caption("Reproduceerbaar: alle stappen staan in dit script; pas filters/winsorisatie aan in de sidebar.")

# KPI's
with st.container(border=True):
    st.markdown("#### Overzicht statistieken")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rijen na filters", f"{len(filtered):,}")
    c2.metric("Unieke airlines", filtered['AIRLINE'].nunique())
    c3.metric("Unieke vertrekluchthavens", filtered['ORIGIN_AIRPORT'].nunique())
    c4.metric("Winsorisatie p%", f"{trim_pct}%")

st.markdown("---")

# Tabs voor overzicht
tab_h1, tab_h2, tab_corr, tab_hour, tab_conc = st.tabs(
    ["Hypothese 1", "Hypothese 2", "Correlatieanalyse", "Uur-samenvatting", "Conclusies"]
)

# ------------------------------
# Hypothese 1
# ------------------------------
with tab_h1:
    st.markdown("### Hypothese 1: Later vertrek leidt tot meer aankomstvertraging (cascade)")
    slope = trend_stats.get("slope")
    r2 = trend_stats.get("r2")
    ctrl_slope = ctrl_stats.get("slope")
    ctrl_r2 = ctrl_stats.get("r2")
    f_stat = anova_stats.get("f_stat")
    p_val = anova_stats.get("p_value")
    eff = anova_stats.get("effect_size")

    c1, c2, c3 = st.columns(3)
    c1.metric("Trend (min/uur)", f"{slope:0.2f}" if slope is not None else "n.v.t.")
    c2.metric("R²", f"{r2:0.3f}" if r2 is not None else "n.v.t.")
    label_anova = f"F={f_stat:0.2f}" if f_stat is not None else "n.v.t."
    if p_val is not None:
        label_anova += f", p={p_val:0.3f}"
    c3.metric("ANOVA vertrekuur", label_anova)
    st.caption("Interpretatie: positieve slope ondersteunt het cascade-effect; ANOVA toont of gemiddelden per vertrekuur verschillen (p-waarde zichtbaar indien SciPy beschikbaar).")
    st.markdown(
        f"- Gecorrigeerde trend (maand + weekdag): **{ctrl_slope:0.2f} min/uur** (R² {ctrl_r2:0.3f})" if ctrl_slope is not None else "- Gecorrigeerde trend niet beschikbaar."
    )

    chart1 = build_scatter_dep_hour(filtered)
    if chart1 is not None:
        st.altair_chart(chart1, use_container_width=True)
    else:
        st.warning("Onvoldoende observaties voor scatter vertrekuur vs. aankomstvertraging.")

    st.info("Conclusie H1: positieve slope en R² > 0 geven steun voor het cascade-effect; combineer dit met ANOVA voor significantie.")
    st.caption("Visualisatie: scatter met regressielijn; hover voor details. Winsorisatie dempt uitschieters.")

# ------------------------------
# Hypothese 2
# ------------------------------
with tab_h2:
    st.markdown("### Hypothese 2: Hubs hebben hogere aankomstvertraging dan niet-hubs")
    st.caption("Definitie hub: top 20% drukste vertrekvelden binnen de gefilterde dataset.")
    hub_chart = build_hub_bar(filtered)
    if hub_chart is not None:
        st.altair_chart(hub_chart, use_container_width=True)
    else:
        st.warning("Onvoldoende observaties om hubs vs. niet-hubs te tonen.")

    # Tabel top luchthavens
    airport_avg = (
        filtered.groupby("ORIGIN_AIRPORT")["ARRIVAL_DELAY"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_arrival_delay", "count": "flights"})
    )
    airport_avg["airport_name"] = airport_avg["ORIGIN_AIRPORT"].map(airport_lookup).fillna(airport_avg["ORIGIN_AIRPORT"])
    airport_avg = airport_avg[airport_avg["flights"] >= 500].sort_values("avg_arrival_delay", ascending=False)
    airport_avg["avg_arrival_delay"] = airport_avg["avg_arrival_delay"].round(2)
    airport_avg["flights"] = airport_avg["flights"].astype(int)
    st.markdown("#### Top vertrekluchthavens (≥500 vluchten, huidige filters)")
    st.dataframe(
        airport_avg.head(15)[["airport_name", "avg_arrival_delay", "flights"]]
        .rename(columns={"airport_name": "Luchthaven", "avg_arrival_delay": "Gem. aankomstvertraging (min)", "flights": "# vluchten"}),
        hide_index=True,
        use_container_width=True,
    )
    st.info("Conclusie H2: hogere gemiddelde vertraging bij hubs ondersteunt de hypothese; weeg ook aantallen vluchten mee.")

# ------------------------------
# Correlatieanalyse
# ------------------------------
with tab_corr:
    st.markdown("### Correlatie: vertrekvertraging en aankomstvertraging")
    if corr_dep_arr is not None:
        st.metric("Pearson r", f"{corr_dep_arr:0.3f}")
        st.caption("Pearson r meet de samenhang; een hoge positieve r wijst op doorwerking van vertrekvertraging naar aankomst.")
    else:
        st.warning("Onvoldoende observaties voor het berekenen van de correlatie.")

    chart_corr = build_scatter_dep_arr(filtered)
    if chart_corr is not None:
        st.altair_chart(chart_corr, use_container_width=True)
    else:
        st.warning("Onvoldoende observaties voor scatter vertrek vs. aankomstvertraging.")

    st.info("Interpretatie: r → 1 = sterke positieve samenhang; r → 0 = zwakke samenhang.")

# ------------------------------
# Uur-samenvatting
# ------------------------------
with tab_hour:
    st.markdown("### Uur-samenvatting")
    if hourly.empty:
        st.warning("Geen uurdata beschikbaar met de huidige filters.")
    else:
        table = hourly[["dep_hour", "mean_arr_delay", "median_arr_delay", "weather_share_pct", "flights"]].copy()
        table["mean_arr_delay"] = table["mean_arr_delay"].round(2)
        table["median_arr_delay"] = table["median_arr_delay"].round(2)
        table["weather_share_pct"] = table["weather_share_pct"].round(2)
        table["flights"] = table["flights"].astype(int)
        st.dataframe(
            table.rename(
                columns={
                    "dep_hour": "Vertrekuur",
                    "mean_arr_delay": "Gem. aankomstvertraging",
                    "median_arr_delay": "Mediaan",
                    "weather_share_pct": "% met weersvertraging",
                    "flights": "# vluchten",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("Toelichting: gemiddelden en mediaan per vertrekuur, inclusief aandeel weersvertraging en aantal vluchten.")

# ------------------------------
# Conclusies
# ------------------------------
with tab_conc:
    st.markdown("### Conclusies en rapportage")
    st.info(
        "- H1: beoordeel slope/R² en ANOVA; noteer of de trend positief en significant is.\n"
        "- H2: vergelijk hubs-bar en top-luchthaventabel; benoem welke hubs het slechtst scoren en de omvang van de hubgroep.\n"
        "- Correlatie: rapporteer Pearson r en koppel deze aan de doorwerking van vertrekvertraging.\n"
        "- Documenteer cleaning (winsorisatie p%, filters) en bron (flights.csv 2015 + labels) in je verslag/presentatie."
    )
