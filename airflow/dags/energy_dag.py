import sys, os
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

#  ─────────────────────────────────────────────────────────
#  Make sure Python can find the `dags/tasks` package
#  ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))  # adds `/opt/airflow/dags` to PYTHONPATH

# Now `tasks` is a top-level package
from tasks.update_db import update_energy_data

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

with DAG(
    dag_id='update_energy_data_dag',
    default_args=default_args,
    description='Fetch + upsert electricity data into Postgres',
    schedule_interval='0 0,12 * * *',  # midnight & noon daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['energy', 'postgres'],
) as dag:

    run_update = PythonOperator(
        task_id='run_update_energy_data',
        python_callable=update_energy_data,
    )

    run_update
