from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os

# Importeer jouw eigen functies (zorg dat dit pad klopt in jouw project)
from tasks.historical_predictions import run_forecast_pipeline

# Definieer default_args
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

# Definieer de DAG
with DAG(
    dag_id='daily_forecast_dag',
    default_args=default_args,
    description='Daily load forecast using weather data',
    schedule_interval='0 5 * * *',  # Elke dag om 5:00 's ochtends
    start_date=datetime(2024, 4, 29),
    catchup=False,
    tags=['forecasting', 'load', 'weather']
) as dag:

    def forecast_task():
        run_forecast_pipeline(

            model_path='/opt/airflow/dags/models/best_xgb_model.pkl',  # Pas aan naar jouw model pad
            weather_table='public.weather_data',
            prediction_table='historical_load_predictions'
        )

    run_forecast = PythonOperator(
        task_id='run_load_forecast',
        python_callable=forecast_task
    )

    run_forecast
