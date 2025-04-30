import pickle
from datetime import datetime
import pandas as pd
import xgboost as xgb
import tasks.sql as sql

# assume these helper functions are already defined:
#   load_table(table_name: str) -> pd.DataFrame
#   upsert_dataframe(df: pd.DataFrame, table_name: str, conflict_columns: str, db_config: dict, schema_name: str)

SELECTED_FEATURES = [
    'hour', 'day_of_week', 'month', 'is_weekend', 'is_holiday',
    'T', 'heating_degree', 'cooling_degree'
]

def get_weather_data(table_name: str) -> pd.DataFrame:
    """
    Load raw weather (or forecasted) data from the database.
    """
    df = sql.load_table(table_name)
    return df

def build_feature_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature DataFrame ready for prediction.
    Assumes raw_df has a 'timestamp' column (not as index) and 'T' (temperature) column.
    """
    df = raw_df.copy()

    # Zorg dat timestamp kolom datetime type is
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')

    df['T'] = df['t']

    # Tijd features uit timestamp kolom
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

    

    import holidays

    # Nederlandse feestdagen
    nl_holidays = holidays.country_holidays('NL')

    # 2. Zorg dat 'timestamp' een datetime64[ns] type is
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

    # 3. Functie om te checken of het een feestdag is
    def is_holiday(timestamp):
        if pd.isna(timestamp):
            return 0  # Als timestamp NaT is, dan geen feestdag
        return int(timestamp.date() in nl_holidays)

    # 4. Voeg feestdag kolom toe
    df['is_holiday'] = df['timestamp'].apply(is_holiday)

    # Heating / cooling degrees
    df['heating_degree'] = (18 - df['T']).clip(lower=0)
    df['cooling_degree'] = (df['T'] - 22).clip(lower=0)

    # Drop NaNs
    df = df[SELECTED_FEATURES + ['timestamp']]
    df = df.dropna()

    return df


def load_xgb_model(path: str) -> xgb.XGBRegressor:
    """
    Load the pickled XGBoost model from disk.
    """
    with open(path, 'rb') as f:
        model = pickle.load(f)
    return model

def predict_load(feature_df: pd.DataFrame, model: xgb.XGBRegressor) -> pd.DataFrame:
    """
    Run the model to predict load for each timestamp in feature_df.
    Ensures 'timestamp' is datetime type and returns a clean DataFrame.
    """

    print(feature_df.columns)
    # Check of 'timestamp' kolom bestaat
    if 'timestamp' not in feature_df.columns:
        raise ValueError("Feature dataframe must contain a 'timestamp' column.")

    # Zorg dat 'timestamp' datetime64[ns] is
    feature_df['timestamp'] = pd.to_datetime(feature_df['timestamp'], errors='coerce')

    # Check op eventuele NaT timestamps
    if feature_df['timestamp'].isna().any():
        raise ValueError("Some timestamps could not be converted to datetime.")

    # Selecteer features en predict
    X = feature_df[SELECTED_FEATURES]
    preds = model.predict(X)

    # Bouw clean output
    return pd.DataFrame({
        'timestamp': feature_df['timestamp'].values,
        'predicted_load': preds
    })


def write_predictions_to_db(predictions: pd.DataFrame,
                            table_name: str,
                            db_config: dict):
    """
    Upsert the predicted_load DataFrame into the given table,
    making sure 'timestamp' is TIMESTAMP WITH TIME ZONE.
    """
    # 1. Force timestamp column to UTC tz-aware datetime
    predictions['timestamp'] = pd.to_datetime(
        predictions['timestamp'], errors='coerce', utc=True
    )

    # 2. Drop any rows where timestamp conversion failed
    predictions = predictions.dropna(subset=['timestamp'])

    # 3. Reset index and upsert
    sql.upsert_dataframe(
        df=predictions.reset_index(drop=True),
        table_name=table_name,
        conflict_columns='timestamp',
        db_config=db_config,
        schema_name='public'
    )

def run_forecast_pipeline(
                          model_path: str,
                          weather_table: str,
                          prediction_table: str):
    


    db_config = {
        "dbname": "energy", 
        "user": "rayen",
        "password": "xxx",
        "host": "172.17.0.1",
        "port": "5432"
    }

    """
    Main entrypoint: load weather, build features, load model,
    predict load, and write to the database.
    """
    # 1. Load weather (or forecast) data
    raw_weather = get_weather_data(weather_table)

    # 2. Build feature DataFrame
    feature_df = build_feature_dataframe(raw_weather)

    # 3. Load trained model
    model = load_xgb_model(model_path)

    # 4. Predict load
    predictions = predict_load(feature_df, model)

    

    # 5. Add generation timestamp
    # predictions['generation_time'] = datetime.utcnow()

    # 6. Write into DB
    write_predictions_to_db(predictions, prediction_table, db_config)


