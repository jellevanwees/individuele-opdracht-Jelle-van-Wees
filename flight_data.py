import pandas as pd
import streamlit as st
from pathlib import Path

# Shared data loading utilities for the flight delay project.

DATA_DIR = Path(__file__).resolve().parent
FLIGHTS_FILE = DATA_DIR / "flights.csv"
AIRLINES_FILE = DATA_DIR / "airlines.csv"
AIRPORTS_FILE = DATA_DIR / "airports.csv"


@st.cache_data(show_spinner=False)
def load_airline_lookup():
    df = pd.read_csv(AIRLINES_FILE)
    return dict(zip(df["IATA_CODE"], df["AIRLINE"]))


@st.cache_data(show_spinner=False)
def load_airport_lookup():
    df = pd.read_csv(AIRPORTS_FILE)
    return dict(zip(df["IATA_CODE"], df["AIRPORT"]))


@st.cache_data(show_spinner=True)
def load_flights(max_rows=300000):
    df = pd.read_csv(FLIGHTS_FILE, nrows=max_rows)
    numeric_cols = [
        "SCHEDULED_DEPARTURE",
        "DEPARTURE_DELAY",
        "ARRIVAL_DELAY",
        "WEATHER_DELAY",
        "LATE_AIRCRAFT_DELAY",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[(df["CANCELLED"] == 0) & (df["DIVERTED"] == 0)]
    df = df.dropna(subset=["ARRIVAL_DELAY", "SCHEDULED_DEPARTURE"])

    df["dep_hour"] = (df["SCHEDULED_DEPARTURE"] // 100).clip(lower=0, upper=23).astype(int)
    df["is_late_15"] = df["ARRIVAL_DELAY"] > 15
    df["has_weather_delay"] = df["WEATHER_DELAY"].fillna(0) > 0
    df["has_late_aircraft_delay"] = df["LATE_AIRCRAFT_DELAY"].fillna(0) > 0
    return df


@st.cache_data(show_spinner=False)
def load_preview(n_rows=5000):
    """Lightweight preview subset for intro/stats pages."""
    return load_flights(max_rows=n_rows)
