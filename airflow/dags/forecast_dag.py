from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os

# Import the task function you just wrote
from tasks.forecast import future_forecast_task

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='hourly_forecast_dag',
    default_args=default_args,
    description='Hourly 24h load forecast using Open-Meteo data',
    schedule_interval='@hourly',
    start_date=datetime(2025, 4, 28, 0, 0),
    catchup=False,
    tags=['forecasting', 'load', 'weather']
) as dag:

    run_hourly_forecast = PythonOperator(
        task_id='run_future_load_forecast',
        python_callable=future_forecast_task
    )

    run_hourly_forecast
