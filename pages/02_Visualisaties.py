import altair as alt
import pandas as pd
import streamlit as st

from flight_data import load_airline_lookup, load_airport_lookup, load_flights

st.set_page_config(page_title="Visualisaties — Flight Delays", layout="wide", page_icon="📊")
st.title("Visualisaties — Flight Delay Dashboard")
st.caption("Interactie en grafieken voor de twee hypothesen.")


def hourly_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "dep_hour",
                "mean_arr_delay",
                "median_arr_delay",
                "weather_share",
                "late_aircraft_share",
                "flights",
                "weather_share_pct",
                "late_aircraft_share_pct",
            ]
        )
    hourly = (
        df.groupby("dep_hour")
        .agg(
            mean_arr_delay=("ARRIVAL_DELAY", "mean"),
            median_arr_delay=("ARRIVAL_DELAY", "median"),
            weather_share=("has_weather_delay", "mean"),
            late_aircraft_share=("has_late_aircraft_delay", "mean"),
            flights=("ARRIVAL_DELAY", "size"),
        )
        .reset_index()
        .sort_values("dep_hour")
    )
    hourly["weather_share_pct"] = hourly["weather_share"] * 100
    hourly["late_aircraft_share_pct"] = hourly["late_aircraft_share"] * 100
    return hourly


def build_hourly_chart(hourly: pd.DataFrame):
    blue = "#2f4b7c"
    orange = "#f28e2c"
    base = alt.Chart(hourly).encode(
        x=alt.X("dep_hour:O", title="Vertrekuur (0–23)"),
        tooltip=[
            "dep_hour:O",
            alt.Tooltip("mean_arr_delay:Q", format=".1f", title="Gem. vertraging"),
            alt.Tooltip("median_arr_delay:Q", format=".1f", title="Mediaan"),
            alt.Tooltip("flights:Q", format=",.0f", title="# vluchten"),
        ],
    )
    mean_line = base.mark_line(color=blue, point=True).encode(y=alt.Y("mean_arr_delay:Q", title="Gem. aankomstvertraging (minuten)"))
    median_line = base.mark_line(color=orange, strokeDash=[4, 2]).encode(y="median_arr_delay:Q")
    trend = (
        alt.Chart(hourly)
        .transform_regression("dep_hour", "mean_arr_delay")
        .mark_line(color=orange, strokeDash=[6, 3])
        .encode(x=alt.X("dep_hour:O"), y="mean_arr_delay:Q")
    )
    zero_rule = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#cccccc", strokeDash=[2, 2]).encode(y="y:Q")
    return (zero_rule + mean_line + median_line + trend).properties(title="Aankomstvertraging vs. vertrekuur")


def build_weather_chart(hourly: pd.DataFrame):
    green = "#66a182"
    chart = (
        alt.Chart(hourly)
        .mark_bar(color=green)
        .encode(
            x=alt.X("dep_hour:O", title="Vertrekuur (0–23)"),
            y=alt.Y("weather_share_pct:Q", title="% vluchten met weersvertraging"),
            tooltip=[
                "dep_hour:O",
                alt.Tooltip("weather_share_pct:Q", format=".1f", title="% met weersvertraging"),
                alt.Tooltip("flights:Q", format=",.0f", title="# vluchten"),
            ],
        )
        .properties(title="Weervertraging (% vluchten) per vertrekuur")
    )
    return chart


def build_reactionary_chart(hourly: pd.DataFrame):
    orange = "#f28e2c"
    chart = (
        alt.Chart(hourly)
        .mark_bar(color=orange)
        .encode(
            x=alt.X("dep_hour:O", title="Vertrekuur (0–23)"),
            y=alt.Y("late_aircraft_share_pct:Q", title="% vluchten met late aircraft delay"),
            tooltip=[
                "dep_hour:O",
                alt.Tooltip("late_aircraft_share_pct:Q", format=".1f", title="% late aircraft delay"),
                alt.Tooltip("flights:Q", format=",.0f", title="# vluchten"),
            ],
        )
        .properties(title="Reactionary delay (late aircraft) per vertrekuur")
    )
    return chart


def build_airline_chart(df: pd.DataFrame, lookup: dict, min_flights: int):
    orange = "#f28e2c"
    agg = (
        df.groupby("AIRLINE")["ARRIVAL_DELAY"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_delay"})
    )
    agg = agg[agg["count"] >= min_flights]
    agg["airline_name"] = agg["AIRLINE"].map(lookup).fillna(agg["AIRLINE"])
    agg = agg.sort_values("avg_delay", ascending=False).head(20)
    chart = (
        alt.Chart(agg)
        .mark_bar(color=orange)
        .encode(
            y=alt.Y("airline_name:N", sort="-x", title="Airline"),
            x=alt.X("avg_delay:Q", title="Gem. aankomstvertraging (min)"),
            tooltip=[
                alt.Tooltip("airline_name:N", title="Airline"),
                alt.Tooltip("avg_delay:Q", format=".1f", title="Gem. aankomstvertraging (min)"),
                alt.Tooltip("count:Q", format=",.0f", title="# vluchten"),
            ],
        )
        .properties(title="Airlines op vertraging")
    )
    return chart


def build_airport_chart(df: pd.DataFrame, lookup: dict, min_flights: int):
    blue = "#2f4b7c"
    agg = (
        df.groupby("ORIGIN_AIRPORT")["ARRIVAL_DELAY"]
        .agg(["mean", "count"])
        .reset_index()
        .rename(columns={"mean": "avg_delay"})
    )
    agg = agg[agg["count"] >= min_flights]
    # Markeer hubs als top 20% drukste vertrekvelden in de gefilterde dataset
    hub_threshold = agg["count"].quantile(0.8) if not agg.empty else None
    agg["is_hub"] = agg["count"] >= hub_threshold if hub_threshold is not None else False
    agg["airport_name"] = agg["ORIGIN_AIRPORT"].map(lookup).fillna(agg["ORIGIN_AIRPORT"])
    agg = agg.sort_values("avg_delay", ascending=False).head(15)
    chart = (
        alt.Chart(agg)
        .mark_bar(color=blue)
        .encode(
            y=alt.Y("airport_name:N", sort="-x", title="Vertrek-luchthaven"),
            x=alt.X("avg_delay:Q", title="Gem. aankomstvertraging (min)"),
            tooltip=[
                alt.Tooltip("airport_name:N", title="Luchthaven"),
                alt.Tooltip("avg_delay:Q", format=".1f", title="Gem. aankomstvertraging (min)"),
                alt.Tooltip("count:Q", format=",.0f", title="# vluchten"),
                alt.Tooltip("is_hub:N", title="Hub (top 20% volume)"),
            ],
        )
        .properties(title="Luchthavens met hoogste vertraging")
    )
    return chart


with st.sidebar:
    st.header("Instellingen")
    st.caption("Gebruik de rijlimiet voor snelheid vs. nauwkeurigheid.")
    row_limit = st.number_input(
        "Rijen laden (flights.csv)",
        min_value=50000,
        max_value=1000000,
        value=100000,
        step=50000,
        key="row_limit_vis",
        help="Kies minder rijen voor snellere interactie; meer rijen voor nauwkeuriger gemiddelden.",
    )
    st.caption("Cache voorkomt herladen bij filteren; pas rijen aan voor snelheid vs. precisie.")

df = load_flights(int(st.session_state.get("row_limit_vis", row_limit)))
airline_lookup = load_airline_lookup()
airport_lookup = load_airport_lookup()

month_options = sorted(df["MONTH"].dropna().unique().tolist())
airline_options = sorted(df["AIRLINE"].dropna().unique().tolist())
origin_options = sorted(df["ORIGIN_AIRPORT"].dropna().unique().tolist())
dest_options = sorted(df["DESTINATION_AIRPORT"].dropna().unique().tolist())

default_state = {
    "months": month_options,
    "airlines": [],
    "origins": [],
    "destinations": [],
    "min_flights_airline": 500,
    "min_flights_airport": 800,
}

with st.sidebar:
    st.markdown("### Filters")
    st.caption("Laat alles aan voor een representatief totaalbeeld; verfijn per behoefte.")

    if st.button("🔄 Reset filters", type="secondary"):
        for key, val in default_state.items():
            st.session_state[key] = val
        st.rerun()

    months = st.multiselect("Maanden", options=month_options, default=st.session_state.get("months", month_options), key="months")
    st.caption("Alle maanden aan = volledig jaar.")

    airlines = st.multiselect(
        "Airlines",
        options=airline_options,
        default=st.session_state.get("airlines", []),
        format_func=lambda x: f"{x} — {airline_lookup.get(x, x)}",
        key="airlines",
    )
    st.caption("Leeg laten = alle airlines.")

    origins = st.multiselect("Vertrekluchthavens", options=origin_options, default=st.session_state.get("origins", []), format_func=lambda x: airport_lookup.get(x, x), key="origins")
    st.caption("Leeg laten = alle vertrekluchthavens.")

    destinations = st.multiselect("Bestemmingen", options=dest_options, default=st.session_state.get("destinations", []), format_func=lambda x: airport_lookup.get(x, x), key="destinations")
    st.caption("Leeg laten = alle bestemmingen.")

    min_flights_airline = st.slider("Min. vluchten per airline", 50, 5000, st.session_state.get("min_flights_airline", 500), step=50, key="min_flights_airline")
    st.caption("Drempel om kleine airlines uit de ranking te houden.")

    min_flights_airport = st.slider("Min. vluchten per luchthaven", 50, 5000, st.session_state.get("min_flights_airport", 800), step=50, key="min_flights_airport")
    st.caption("Drempel om luchthavens met weinig vluchten te filteren.")


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    out = data
    if months:
        out = out[out["MONTH"].isin(months)]
    if airlines:
        out = out[out["AIRLINE"].isin(airlines)]
    if origins:
        out = out[out["ORIGIN_AIRPORT"].isin(origins)]
    if destinations:
        out = out[out["DESTINATION_AIRPORT"].isin(destinations)]
    return out


filtered = apply_filters(df)
hourly = hourly_summary(filtered)
route_agg = (
    filtered.groupby(["ORIGIN_AIRPORT", "DESTINATION_AIRPORT"])["ARRIVAL_DELAY"]
    .agg(["mean", "count"])
    .reset_index()
    .rename(columns={"mean": "avg_arrival_delay", "count": "flights"})
)
route_agg["origin_name"] = route_agg["ORIGIN_AIRPORT"].map(airport_lookup).fillna(route_agg["ORIGIN_AIRPORT"])
route_agg["dest_name"] = route_agg["DESTINATION_AIRPORT"].map(airport_lookup).fillna(route_agg["DESTINATION_AIRPORT"])
route_agg = route_agg[route_agg["flights"] >= 100]
route_table = route_agg.sort_values("avg_arrival_delay", ascending=False).head(20)

with st.container(border=True):
    st.markdown("### KPI's (gefilterd)")
    st.caption("Alle KPI's zijn gebaseerd op de huidige filters, na verwijderen van geannuleerde/omgeleide vluchten.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vluchten", f"{len(filtered):,}")
    late_pct = filtered["is_late_15"].mean() * 100 if len(filtered) else 0
    c2.metric(">15 min vertraagd", f"{late_pct:0.1f}%")
    dep_delay = filtered["DEPARTURE_DELAY"].mean() if len(filtered) else 0
    arr_delay = filtered["ARRIVAL_DELAY"].mean() if len(filtered) else 0
    c3.metric("Gem. vertrekvertraging", f"{dep_delay:0.1f} min")
    c4.metric("Gem. aankomstvertraging", f"{arr_delay:0.1f} min")
    st.caption("Op basis van de huidige filters (geannuleerd/omgeleid verwijderd).")

st.markdown("---")

st.markdown("### Hypothese 1: Vertraging vs. tijd en weer")
with st.container(border=True):
    col_left, col_right = st.columns(2)
    with col_left:
        st.altair_chart(build_hourly_chart(hourly), use_container_width=True)
    with col_right:
        st.altair_chart(build_weather_chart(hourly), use_container_width=True)
    st.altair_chart(build_reactionary_chart(hourly), use_container_width=True)
    st.caption(
        "Hypothese 1: links zie je de gemiddelde aankomstvertraging per vertrekuur (cascade-effect), met trendlijn. "
        "Rechts het % vluchten met een geregistreerde weersvertraging per vertrekuur. "
        "Onder: reactionary delay (late aircraft) als indicator voor kettingvertraging; de eerste vlucht op tijd helpt dit beperken, "
        "met extra impact op slot-coordinated luchthavens. Hover voor exacte waarden."
    )

st.markdown("---")

st.markdown("### Hypothese 2: Airlines en luchthavens")
with st.container(border=True):
    col_a, col_b = st.columns(2)
    with col_a:
        st.altair_chart(build_airline_chart(filtered, airline_lookup, min_flights_airline), use_container_width=True)
    with col_b:
        st.altair_chart(build_airport_chart(filtered, airport_lookup, min_flights_airport), use_container_width=True)
    st.caption(
        "Hypothese 2: hubs met veel verkeer kunnen hogere gemiddelde aankomstvertraging laten zien. "
        "Links: top airlines gesorteerd op gemiddelde aankomstvertraging (bovenaan slechtste). "
        "Rechts: top vertrekluchthavens gesorteerd op vertraging; tooltip toont # vluchten en of het een hub is (top 20% volume). "
        "Hover voor gemiddelden en aantallen binnen de huidige filters."
    )

st.markdown("---")

st.markdown("### Top-routes met vertraging")
with st.container(border=True):
    st.caption("Routes met ≥100 vluchten (binnen huidige filters), gesorteerd op hoogste gemiddelde aankomstvertraging.")
    st.dataframe(
        route_table[["origin_name", "dest_name", "avg_arrival_delay", "flights"]]
        .rename(
            columns={
                "origin_name": "Origin",
                "dest_name": "Destination",
                "avg_arrival_delay": "Avg arrival delay (min)",
                "flights": "# flights",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Routes met minstens 100 vluchten; sorteerbaar en filterbaar via de sidebar.")

with st.container(border=True):
    st.subheader("Export")
    st.download_button(
        "Download gefilterde vluchten (CSV)",
        data=filtered.to_csv(index=False),
        file_name="flights_filtered.csv",
        mime="text/csv",
        help="Volledige rijenset na toepassing van filters (geannuleerd/omgeleid verwijderd). Gebruik voor eigen grafieken of tabellen.",
    )
    st.download_button(
        "Download uur-samenvatting (CSV)",
        data=hourly.to_csv(index=False),
        file_name="hourly_summary_filtered.csv",
        mime="text/csv",
        help="Gemiddelde/median vertraging per vertrekuur en % weersvertraging na filters. Handig voor trendplots in PowerPoint of rapport.",
    )
    st.download_button(
        "Download top-routes tabel (CSV)",
        data=route_table.to_csv(index=False),
        file_name="top_routes_filtered.csv",
        mime="text/csv",
        help="Top-routes met gemiddelde aankomstvertraging en # vluchten (≥100) na filters. Gebruik voor tabel/figuur op A1.",
    )
    st.caption(
        "Gebruik deze exports om figuren te maken in PowerPoint/rapport of om de A1-poster te vullen. "
        "Print de pagina als PDF als je de exacte grafieken wilt vastleggen voor de inlevering."
    )

st.info("Tip: verlaag de rijen-limiet in de sidebar voor snelle demo's, of verhoog voor nauwkeuriger cijfers.")
