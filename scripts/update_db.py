# ~/airflow/dags/tasks/db_updater.py

from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

import main  # assumes your main.py is in PYTHONPATH or dags/
import generation, load  # if u     sed inside main.load_tables()
import sql


def update_energy_data():

    today = datetime.today()
    two_weeks_ago = today - timedelta(days=14)

    d_start = two_weeks_ago.strftime("%d").zfill(2)
    m_start = two_weeks_ago.strftime("%m").zfill(2)
    y_start = two_weeks_ago.strftime("%Y")

    d_end = today.strftime("%d").zfill(2)
    m_end = today.strftime("%m").zfill(2)
    y_end = today.strftime("%Y")


    tables = main.load_tables(m_start, d_start, m_end, d_end, y_start, y_end)

    db_config = {
        "dbname": "energy",
        "user": "rayen",
        "password": "xxx",
        "host": "host.docker.internal",  # IMPORTANT: resolves to your host machine inside Docker
        "port": "5432"
    }

    for table_name, df_data in tables.items():
        print(f"📥 Upserting {table_name} ...")
        sql.upsert_dataframe(df_data, table_name, "timestamp", db_config)

if __name__ == "__main__":

    update_energy_data()