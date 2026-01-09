from pathlib import Path

import pandas as pd
import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

FLIGHTS_FILE = DATA_DIR / "flights.csv"
AIRLINES_FILE = BASE_DIR / "airlines.csv"
AIRPORTS_FILE = BASE_DIR / "airports.csv"

FLIGHTS_URL = (
    "https://github.com/jellevanwees/individuele-opdracht-Jelle-van-Wees/"
    "releases/download/v1.0/flights.csv"
)


def ensure_flights_file():
    if not FLIGHTS_FILE.exists():
        with requests.get(FLIGHTS_URL, stream=True) as r:
            r.raise_for_status()
            with open(FLIGHTS_FILE, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)


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
    ensure_flights_file()

    df = pd.read_csv(FLIGHTS_FILE, nrows=max_rows)

    numeric_cols = [
        "SCHEDULED_DEPARTURE",
        "DEPARTURE_DELAY",
        "ARRIVAL_DELAY",
        "WEATHER_DELAY",
        "LATE_AIRCRAFT_DELAY",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "CANCELLED" in df.columns:
        df = df[df["CANCELLED"] == 0]
    if "DIVERTED" in df.columns:
        df = df[df["DIVERTED"] == 0]

    drop_cols = [c for c in ["ARRIVAL_DELAY", "SCHEDULED_DEPARTURE"] if c in df.columns]
    if drop_cols:
        df = df.dropna(subset=drop_cols)

    if "SCHEDULED_DEPARTURE" in df.columns:
        df["dep_hour"] = (
            (df["SCHEDULED_DEPARTURE"] // 100)
            .clip(lower=0, upper=23)
            .astype(int)
        )

    if "ARRIVAL_DELAY" in df.columns:
        df["is_late_15"] = df["ARRIVAL_DELAY"] > 15

    if "WEATHER_DELAY" in df.columns:
        df["has_weather_delay"] = df["WEATHER_DELAY"].fillna(0) > 0

    if "LATE_AIRCRAFT_DELAY" in df.columns:
        df["has_late_aircraft_delay"] = df["LATE_AIRCRAFT_DELAY"].fillna(0) > 0

    return df


@st.cache_data(show_spinner=False)
def load_preview(n_rows=5000):
    return load_flights(max_rows=n_rows)
