import requests
import pandas as pd
import pickle
from datetime import datetime, timedelta
from tasks.sql import upsert_dataframe

# Constants
LATITUDE = 52.1
LONGITUDE = 5.18

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast?"
    f"latitude={LATITUDE}&longitude={LONGITUDE}"
    "&hourly=temperature_2m,precipitation,shortwave_radiation,"
    "direct_radiation,diffuse_radiation,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
)

MODEL_PATH = "/opt/airflow/dags/models/best_xgb_model.pkl"

SELECTED_FEATURES = [
    'hour', 'day_of_week', 'month', 'is_weekend', 'is_holiday',
    'T', 'heating_degree', 'cooling_degree'
]
DB_CONFIG = {
    "dbname": "energy",
    "user": "rayen",
    "password": "xxx",
    "host": "172.17.0.1",
    "port": "5432"
}

def future_forecast_task():
    """
    Airflow task: fetch next-24h weather forecast, build features,
    load XGB model, predict load, and upsert into SQL.
    """
    # 1. Fetch forecasted weather
    resp = requests.get(OPEN_METEO_URL)
    resp.raise_for_status()
    data = resp.json()

    forecast_df = pd.DataFrame(data['hourly'])
    forecast_df['time'] = pd.to_datetime(forecast_df['time'], errors='coerce')

    # 2. Filter for next 24 hours
    now = datetime.utcnow()
    cutoff = now + timedelta(hours=48)
    forecast_24h = forecast_df[
        (forecast_df['time'] >= now) &
        (forecast_df['time'] <= cutoff)
    ].copy()

    # 3. Build features from 'time' column
    df = forecast_24h.copy()
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    df['month'] = df['time'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5,6]).astype(int)
    df['is_holiday'] = 0  # or implement holiday logic here

    # Temperature & degree features
    df['T'] = df['temperature_2m']*10
    df['heating_degree'] = (180 - df['T']).clip(lower=0)
    df['cooling_degree'] = (df['T'] - 220).clip(lower=0)
    df['t'] = df['T']

    # 4. Load model & predict
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    X = df[SELECTED_FEATURES]
    df['predicted_load'] = model.predict(X)

    # 5. Upsert predictions into SQL
    to_upsert = df[['time', 'predicted_load', 't']].rename(columns={'time':'timestamp'})
    # ensure timestamp is timezone‐aware UTC
    to_upsert['timestamp'] = pd.to_datetime(to_upsert['timestamp'], utc=True)
    upsert_dataframe(
        df=to_upsert,
        table_name="forecasted_load",
        conflict_columns="timestamp",
        db_config=DB_CONFIG,
        schema_name="public"
    )
