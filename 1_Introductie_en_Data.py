import numpy as np
import pandas as pd
import streamlit as st

from flight_data import load_airline_lookup, load_airport_lookup, load_preview

st.set_page_config(page_title="Introductie & Data — Flight Delays", layout="wide", page_icon="✈️")
st.title("Flight Delay Dashboard (VS 2015)")
st.caption("Individuele opdracht — Jelle van Wees")

df_sample = load_preview()

kp1, kp2, kp3, kp4 = st.columns(4)
kp1.metric("Rijen (sample)", f"{len(df_sample):,}")
kp2.metric("Unieke airlines", df_sample["AIRLINE"].nunique(dropna=True))
kp3.metric("Unieke vertrekluchthavens", df_sample["ORIGIN_AIRPORT"].nunique(dropna=True))
avg_missing_pct = df_sample.isnull().mean().mean() * 100 if not df_sample.empty else 0
kp4.metric("Gem. missend (%)", f"{avg_missing_pct:.1f}")

st.markdown(
    """
    ### Context
    Dit project onderzoekt vertragingen in de Verenigde Staten (2015) en toetst twee hypotheses:

    1) **Cascade-effect**: later op de dag geplande vluchten hebben een hogere aankomstvertraging.  
    2) **Hubs vs. kleinere velden**: grote vertrek-hubs hebben gemiddeld hogere aankomstvertraging dan kleinere luchthavens, gecorrigeerd voor vertrektijd.
    """
)

st.markdown("---")

with st.container(border=True):
    st.markdown("### Projectdoel")
    st.markdown(
        """
        - Data snel verkennen en kwaliteit toetsen.  
        - Interactieve visualisaties bouwen voor vertraging vs. vertrekuur, airline en luchthaven.  
        - Eenvoudige statistische checks (trend/ANOVA) om de hypotheses te ondersteunen.  
        - Exporteerbare tabellen/grafieken voor de presentatie en A1-PDF.
        """
    )

st.markdown("---")

# Data preview (kleine subset voor snelheid)
df = df_sample
airline_lookup = load_airline_lookup()
airport_lookup = load_airport_lookup()

with st.container(border=True):
    st.markdown("### Datakaarten in één oogopslag")
    total_records = len(df)
    airlines = df["AIRLINE"].nunique(dropna=True)
    origins = df["ORIGIN_AIRPORT"].nunique(dropna=True)
    avg_missing = df.isnull().mean().mean() * 100 if not df.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Aantal vluchten (sample)", f"{total_records:,}")
    with c2:
        st.metric("Airlines", airlines)
    with c3:
        st.metric("Vertrekluchthavens", origins)
    with c4:
        st.metric("Gem. missend (%%)", f"{avg_missing:.1f}")

st.markdown("---")

with st.container(border=True):
    st.markdown("### Data-audit")
    tab_preview, tab_stats, tab_missing = st.tabs(["📄 Preview", "📊 Statistieken", "⚠️ Missend (%)"])

    with tab_preview:
        st.dataframe(df.head(), hide_index=True)
        st.caption("Eerste vijf rijen van de sample.")

    with tab_stats:
        st.dataframe(df.describe(include="all").transpose(), hide_index=False)
        st.caption("Volledige describe() van de sample (numeriek/categorisch).")

    with tab_missing:
        miss = (df.isnull().mean() * 100).reset_index()
        miss.columns = ["Kolom", "Percentage missend"]
        miss = miss.sort_values("Percentage missend", ascending=False)
        st.dataframe(miss, hide_index=True)
        st.caption("Missende waarden per kolom (%), gesorteerd aflopend.")

with st.container(border=True):
    st.markdown("### Belangrijkste velden")
    st.markdown(
        """
        - `SCHEDULED_DEPARTURE` → vertrekuur (0–23)  
        - `DEPARTURE_DELAY` en `ARRIVAL_DELAY` → vertrek- en aankomstvertraging in minuten  
        - `ORIGIN_AIRPORT`, `DESTINATION_AIRPORT`, `AIRLINE` → joins voor labels  
        - `WEATHER_DELAY` → indicator voor weersvertraging  
        - Afleidingen: `dep_hour`, `is_late_15` (arrival_delay > 15), `has_weather_delay`
        """
    )

st.markdown("---")

with st.expander("🔧 Data cleaning stappen", expanded=False):
    st.markdown(
        """
        - Geannuleerde (`CANCELLED==1`) en omgeleide (`DIVERTED==1`) vluchten verwijderd.  
        - `dep_hour` afgeleid uit `SCHEDULED_DEPARTURE` (hhmm → 0–23).  
        - `is_late_15` gemaakt als indicator voor aankomstvertraging > 15 minuten.  
        - Kolommen met veel missende waarden: bewust gelaten voor transparantie; bij analyse worden kernkolommen zonder grote gaten gebruikt.  
        """
    )

st.markdown("---")

with st.container(border=True):
    st.markdown("### Hoe te gebruiken")
    st.markdown(
        """
        - Ga naar de pagina **Visualisaties** voor interactieve grafieken en KPI's.  
        - Ga naar **Statistische Analyse** voor trend/ANOVA output op de eerste hypothese.  
        - Ga naar **Conclusie** voor samenvatting en exporttips.
        """
    )

st.info("Opmerking: deze intro gebruikt een kleinere sample (5k) voor snelheid; de Visualisaties-pagina laadt meer data.")
