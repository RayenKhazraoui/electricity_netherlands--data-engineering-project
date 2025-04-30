import tasks.load as load
import tasks.generation as generation
import pandas as pd
import matplotlib.pyplot as plt
import tasks.marketing as mk
import knmi


import pandas as pd

def move_timestamp_to_first_column(df, timezone='UTC'):
    """
    - Converteert 'timestamp'-kolom naar datetime (indien aanwezig).
    - Localiseert 'timestamp'-kolom naar de opgegeven timezone.
    - Verplaatst de 'timestamp'-kolom naar de eerste positie in het DataFrame.
    """
    if 'timestamp' in df.columns:
        # Convert naar datetime (zonder tz) 
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Localiseer naar de gewenste timezone (als de kolom nog tz-naïef is)
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(timezone)

        # Eventueel als je al weet dat de timestamps UTC zijn en je wilt converteren
        # naar een andere tijdzone:
        # df['timestamp'] = df['timestamp'].dt.tz_convert(timezone)

        # Zet de timestamp-kolom vooraan
        columns = ['timestamp'] + [col for col in df.columns if col != 'timestamp']
        df = df[columns]
    return df

    
def get_weather_data(m_start, d_start, m_end, d_end, y_start, y_end): 

   # Get weather data

    df_weather = knmi.get_hour_data_dataframe(stations=[260], start=f'{y_start}-{m_start}-{d_start}', end=f'{y_end}-{m_end}-{d_end}')

    # Ensure the index is recognized as a datetime index

    df_weather.index.name = "timestamp"  # Rename index

    # Convert the index into a regular column named "timestamp"

    df_weather = df_weather.reset_index()
    df_weather["timestamp"] = pd.to_datetime(df_weather["timestamp"], unit="s")

    
    return df_weather

def load_tables(m_start, d_start, m_end, d_end, y_start, y_end):


    # Helper function to ensure timestamp is first column

    start = f'{y_start}{m_start}{d_start}0000'
    end = f'{y_end}{m_end}{d_end}2300'

    # Fetch data
    A01_data = move_timestamp_to_first_column(
        load.fetch_and_process_entsoe_data(
            document_type='A65', 
            process_type='A01', 
            start=start,
            end=end
        )
    )

    A16_data = move_timestamp_to_first_column(
        load.fetch_and_process_entsoe_data(
            document_type='A65', 
            process_type='A16', 
            start=start,
            end=end
        )
    )

    generation_data = move_timestamp_to_first_column(
        generation.get_generation_data(start, end)
    )

    market_data = move_timestamp_to_first_column(
        mk.fetch_entsoe_continuous("A44", "A01", start, end, '10YNL----------L')
    )

    weather_data = move_timestamp_to_first_column(
        get_weather_data(m_start, d_start, m_end, d_end, y_start, y_end)
    )

    return {
        "A01_data": A01_data,
        "A16_data": A16_data,
        "generation_data": generation_data,
        "market_data": market_data,
        "weather_data": weather_data
    }