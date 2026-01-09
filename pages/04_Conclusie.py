"""
Conclusiepagina met korte, professionele teksten en klare koppeling aan de hypotheses.
Geschikt als afsluiting van een 8–10 minuten presentatie.
"""

import streamlit as st

st.set_page_config(page_title="Conclusie — Flight Delays", layout="wide", page_icon="✅")
st.title("Conclusie — Flight Delay Dashboard")
st.caption("Kernbevindingen, hypothese-evaluatie, aanbevelingen en take-home message (Jelle van Wees).")

# Samenvatting (bullets)
with st.container(border=True):
    st.markdown("### Samenvatting")
    st.markdown(
        """
        - Vraag: nemen aankomstvertragingen toe bij later vertrek (H1) en hebben hubs hogere vertraging dan niet-hubs (H2)?  
        - Methode: regressie (trend per vertrekuur), ANOVA (verschillen per uur), correlatie (vertrek → aankomst), vergelijking hubs vs. niet-hubs.  
        - Kernbeeld: vertragingen lopen doorgaans op door de dag; drukke hubs tonen hogere gemiddelde aankomstvertraging dan niet-hubs.
        """
    )

# Hypothese 1
with st.container(border=True):
    st.markdown("### Evaluatie Hypothese 1: Later vertrek → meer aankomstvertraging")
    st.markdown(
        """
        - Trend (slope): positieve slope betekent oplopende vertraging per uur; R² toont het (beperkte) verklaarde aandeel.  
        - ANOVA: p < 0,05 wijst op significante verschillen tussen gemiddelde vertraging per vertrekuur.  
        - Interpretatie: positieve slope plus significante ANOVA ondersteunt H1; vlakke of negatieve slope verzwakt H1. Rapporteer ruw én gecorrigeerd (maand/weekdag).
        """
    )

# Hypothese 2
with st.container(border=True):
    st.markdown("### Evaluatie Hypothese 2: Hubs vs. niet-hubs")
    st.markdown(
        """
        - Hubs (top 20% volume) tonen doorgaans enkele minuten extra aankomstvertraging binnen dezelfde filters.  
        - Kijk naar zowel het gemiddelde als het aantal vluchten per groep.  
        - Interpretatie: een duidelijk positief verschil ondersteunt H2; een klein of nulverschil verzwakt H2. Gebruik de hubs-bar en top-luchthaventabel (≥500 vluchten).
        """
    )

# Overige patronen
with st.container(border=True):
    st.markdown("### Overige patronen")
    st.markdown(
        """
        - Correlatie vertrek → aankomst: Pearson r is meestal positief en bevestigt doorwerking van vertrekvertraging.  
        - Weercontext: het aandeel vluchten met weersvertraging per uur verklaart pieken of dalen in de trendlijn.  
        - Routes/airlines: benoem 2–3 structureel vertraagde routes of maatschappijen als illustratie.
        """
    )

# Beperkingen en aanbevelingen
with st.container(border=True):
    st.markdown("### Beperkingen en aanbevelingen")
    st.markdown(
        """
        - Beperkingen: alleen 2015; beperkte weerdetail; geen route-fixed effects; winsorisatie p/p99 dempt uitschieters.  
        - Aanbevelingen: richt buffers op piekuren en hubs; monitor probleemroutes; draai regressies met hogere rijenlimiet; documenteer filters en winsorisatie.
        """
    )

# Conclusie + cijfers (in te vullen)
with st.container(border=True):
    st.markdown("### Conclusie")
    st.markdown(
        """
        - H1: een positieve trend per vertrekuur, ondersteund door een significante ANOVA, wijst op een cascade-effect.  
        - H2: hubs hebben een hogere gemiddelde aankomstvertraging dan niet-hubs; dit ondersteunt de hub-hypothese.  
        - Eindbeeld: vertragingen bouwen op en zijn sterker op drukke hubs; gerichte planning, buffering en monitoring van piekuren zijn noodzakelijk.
        """
    )

# Spreektekst (kort script)
with st.expander("🎤 Spreektekst (kort)"):
    st.markdown(
        """
        - We hebben gekeken of vertragingen oplopen later op de dag en of hubs slechter presteren.  
        - H1: regressies tonen een positieve slope per vertrekuur; ANOVA bevestigt verschillen tussen uren → cascade-effect.  
        - H2: de hubs-barchart en top-luchthaventabel laten hogere gemiddelde vertraging voor hubs zien.  
        - Correlatie: vertrekvertraging werkt door naar aankomst (positieve Pearson r).  
        - Beperkingen: alleen 2015, beperkte weerdetail; winsorisatie temperde uitschieters.  
        - Take-home: vertragingen stapelen zich op, vooral op hubs; focus op piekuren, drukke velden en vaste probleemroutes.
        """
    )

# Reproduceerbaarheid en dataverantwoording
with st.container(border=True):
    st.markdown("### Reproduceerbaarheid en dataverantwoording")
    st.markdown(
        """
        - Dataset: flights.csv (VS 2015) + airlines.csv/airports.csv voor labels.  
        - Cleaning: geannuleerde/omgeleide vluchten verwijderd; numerieke casting; afgeleiden (`dep_hour`, `is_late_15`, `has_weather_delay`); hubs = top 20% volume; winsorisatie p/p99.  
        - Exports: gebruik op de Visualisaties-pagina de CSV-downloads (gefilterde vluchten, uur-samenvatting, top-routes) voor rapportage of A1.  
        - Koppel regressie (slope/R²), ANOVA (F/p) en correlatie (Pearson r) expliciet aan H1/H2 en de bijbehorende visuals/KPI’s in je verslag.
        """
    )
