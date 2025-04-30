# sql commands
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine

DB_NAME = "energy"
DB_USER = "rayen"
DB_PASSWORD = "xxx"
DB_HOST = "172.17.0.1"
DB_PORT = "5432"


def list_tables():

    # Create a database connection
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    # Query to list all tables in the public schema
    query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE';
    """
    
    # Load results into a DataFrame
    df = pd.read_sql(query, engine)
    
    # Return tables as a list
    return df['table_name'].tolist()


def insert_dataframe_with_unique_constraint(df, table_name, unique_columns, db_config, if_exists="replace"):
 
    # Standardize columns
    df = df.copy()  # avoid SettingWithCopyWarning
    df.columns = df.columns.str.lower().str.replace(" ", "_")

    # Convert unique_columns to list if it's a string
    if isinstance(unique_columns, str):
        unique_columns = [unique_columns]

    # Convert timestamp to datetime if present in unique columns
    for col in unique_columns:
        if col in df.columns and col == "timestamp":
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Create the engine
    engine = create_engine(
        f"postgresql://{db_config['user']}:{db_config['password']}@"
        f"{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    )

    # Define a schema (e.g., 'public')
    schema_name = "public"

    # Insert the DataFrame into PostgreSQL
    df.to_sql(table_name, engine, if_exists=if_exists, index=False, schema=schema_name)

    # Build the constraint name
    constraint_name = f"{table_name}_" + "_".join(unique_columns) + "_unique"
    unique_columns_str = ", ".join(unique_columns)

    # Construct the ALTER TABLE query (with schema + quoted table name)
    alter_table_query = f"""
        ALTER TABLE "{schema_name}"."{table_name}"
        ADD CONSTRAINT "{constraint_name}" UNIQUE ({unique_columns_str});
    """

    try:
        conn = psycopg2.connect(
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"]
        )
        cur = conn.cursor()
        cur.execute(alter_table_query)
        conn.commit()
        print(f"✅ Unique constraint added to {unique_columns_str} in {schema_name}.{table_name}!")
    except Exception as e:
        print("❌ Error while adding unique constraint:", e)
    finally:
        cur.close()
        conn.close()

    print(f"✅ DataFrame successfully inserted into '{schema_name}.{table_name}' table!")


def upsert_dataframe(df, table_name, conflict_columns, db_config, schema_name="public"):
    """
    Upserts data from a DataFrame into a PostgreSQL table in the specified schema.
    
    Parameters:
      df (pd.DataFrame): The DataFrame to upsert.
      table_name (str): The name of the target table.
      conflict_columns (str or list): Column(s) to check for conflict (e.g., primary key).
      db_config (dict): Database connection parameters with keys: dbname, user, password, host, port.
      schema_name (str): The PostgreSQL schema where the table resides. Defaults to "public".
    """
    # Make a copy to avoid SettingWithCopyWarning if we're going to mutate columns
    df = df.copy()
    
    # Convert 'timestamp' to datetime if present
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    
    # Standardize column names: lowercase and replace spaces with underscores
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    
    # Convert conflict_columns to list if it is a string
    if isinstance(conflict_columns, str):
        conflict_columns = [conflict_columns]
    
    # Convert DataFrame to list of tuples for SQL execution
    records = df.to_records(index=False).tolist()
    
    # Get column names
    columns = list(df.columns)
    columns_str = ", ".join(columns)
    
    # Build the update clause (exclude conflict columns)
    update_cols = [col for col in columns if col not in conflict_columns]
    update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in update_cols])
    
    # Build the conflict target string
    conflict_str = ", ".join(conflict_columns)
    
    # Construct the UPSERT query with schema + quoted table name
    upsert_query = f"""
    INSERT INTO "{schema_name}"."{table_name}" ({columns_str})
    VALUES %s
    ON CONFLICT ({conflict_str}) DO UPDATE
    SET {update_clause};
    """
    
    # Connect to the database
    try:
        conn = psycopg2.connect(
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"]
        )
        cur = conn.cursor()
        
        # Execute batch upsert
        execute_values(cur, upsert_query, records)
        
        conn.commit()
        print("✅ Data upserted successfully!")
        
    except Exception as e:
        print("❌ Error:", e)
    finally:
        cur.close()
        conn.close()


def load_table(table):



    # Create a database connection using SQLAlchemy
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    # SQL query to load the table
    query = f"SELECT * FROM {table};"

    # Load data into a Pandas DataFrame
    df = pd.read_sql(query, engine)

    return df


def delete_table(table):



    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        print('deleting ',table)

        # SQL query to drop the table
        drop_table_query = f"DROP TABLE IF EXISTS {table} CASCADE;"
        
        # Execute the query
        cur.execute(drop_table_query)
        
        # Commit changes
        conn.commit()
        
        print(f"✅ Table '{table}' dropped successfully!")

        # Close the connection
        cur.close()
        conn.close()

    except Exception as e:
        print("❌ Error:", e)


def reset_database():
    
    DB_CONFIG = {
        "dbname": "energy",
        "user": "rayen",
        "password": "xxx",
        "host": "172.17.0.1",  # IMPORTANT: resolves to your host machine inside Docker
        "port": "5432"
    }

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

        # Force disconnect all users before dropping
        cur.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'mydatabase' AND pid <> pg_backend_pid();
        """)

        cur.execute("DROP DATABASE IF EXISTS mydatabase;")
        cur.execute("CREATE DATABASE mydatabase;")

        print("Database reset successfully.")

        cur.close()
        conn.close()

    except Exception as e:
        print("Error:", e)