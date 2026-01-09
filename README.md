[README.md](https://github.com/user-attachments/files/24531896/README.md)
# Flight Delay Dashboard (US 2015)

Individuele opdracht binnen de Connectivity & Mobility track.  
Project door **Jelle van Wees**.

## Inhoud
- Streamlit-dashboard met Intro, Visualisaties, Statistische Analyse en Conclusie.
- Offline A1‑poster generator (PDF) via `generate_a1_poster.py`.
- Data: `flights.csv`, `airlines.csv`, `airports.csv`.

## Installatie
Gebruik bij voorkeur een virtuele omgeving.

```
pip install streamlit pandas numpy matplotlib altair
```

## Dashboard draaien
Start het dashboard vanaf de intro‑pagina:

```
streamlit run 1_Introductie_en_Data.py
```

De sidebar toont de overige pagina’s.

## A1‑poster (offline PDF)
Genereer de A1‑poster als PDF (geen Streamlit nodig):

```
python generate_a1_poster.py
```

Output:
- `A1_Poster_Flight_Delays_2015.pdf`

## Data cleaning (kort)
- Geannuleerde en omgeleide vluchten verwijderd.
- Afgeleiden: `dep_hour`, `is_late_15`, `has_weather_delay`, `has_late_aircraft_delay`.
- Winsorisatie p1–p99 (in analyses/poster).

## Structuur
- `1_Introductie_en_Data.py`
- `pages/02_Visualisaties.py`
- `pages/03_Statistische_Analyse.py`
- `pages/04_Conclusie.py`
- `flight_data.py`
- `generate_a1_poster.py`

## Dataset
Open data (US 2015). Gebruik bij rapportage:
- U.S. DOT On‑Time Performance Dataset (2015).
- Airlines/airports labels via `airlines.csv` en `airports.csv`.
