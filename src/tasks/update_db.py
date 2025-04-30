from datetime import datetime, timedelta
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# import your helper modules as submodules of `tasks`
import tasks.main as main
import tasks.sql  as sql
import socket

def update_energy_data():

    print('hoi')
    today         = datetime.today()
    two_weeks_ago = today - timedelta(days=1)

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
        "host": "172.17.0.1",
        "port": "5432"
    }

    for table_name, df_data in tables.items():
        print(f"📥 Upserting {table_name} ...")
        sql.upsert_dataframe(df_data, table_name, "timestamp", db_config)

if __name__ == "__main__":
    update_energy_data()
