import requests
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import numpy as np
import xml.etree.ElementTree as ET
import requests
import re

def fetch_entsoe_data(document_type, process_type, start, end, bidding_zone='10YNL----------L'):

    BASE_URL = 'https://web-api.tp.entsoe.eu/api'

    
    API_TOKEN = 'xxx'

    params = {
        'securityToken': API_TOKEN,
        'documentType': document_type,
        'processType': process_type,
        'outBiddingZone_Domain': bidding_zone,
        'periodStart': start,
        'periodEnd': end
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code == 200:
        # print(f"Data {document_type}_{process_type} Retrieved Successfully")
        return response.text
    else:
        print(f"Error: {response.status_code}")
        print(response.text)  # Print full error message for debugging
        return None


def get_namespace(element):
    # Extracts the namespace from the element tag
    m = re.match(r'\{.*\}', element.tag)
    return m.group(0) if m else ''


def parse_timeseries_with_namespace(xml_data):
    root = ET.fromstring(xml_data)
    namespace = get_namespace(root)  # Extract namespace dynamically
    ns = {'ns': namespace[1:-1]}  # Format namespace for findall

    timeseries_list = []

    for time_series in root.findall('.//ns:TimeSeries', ns):
        series_data = {
            'mRID': time_series.find('ns:mRID', ns).text if time_series.find('ns:mRID', ns) is not None else None,
            'businessType': time_series.find('ns:businessType', ns).text if time_series.find('ns:businessType', ns) is not None else None,
            'biddingZone': time_series.find('.//ns:outBiddingZone_Domain.mRID', ns).text if time_series.find('.//ns:outBiddingZone_Domain.mRID', ns) is not None else None,
            'unit': time_series.find('.//ns:price_Measure_Unit.name', ns).text if time_series.find('.//ns:price_Measure_Unit.name', ns) is not None else None,
            'curveType': time_series.find('ns:curveType', ns).text if time_series.find('ns:curveType', ns) is not None else None,
            'periods': []
        }

        # Parse periods and points
        for period in time_series.findall('.//ns:Period', ns):
            start = period.find('.//ns:timeInterval/ns:start', ns).text if period.find('.//ns:timeInterval/ns:start', ns) is not None else None
            end = period.find('.//ns:timeInterval/ns:end', ns).text if period.find('.//ns:timeInterval/ns:end', ns) is not None else None
            resolution = period.find('ns:resolution', ns).text if period.find('ns:resolution', ns) is not None else None

            points = []
            for point in period.findall('.//ns:Point', ns):
                position = point.find('ns:position', ns).text if point.find('ns:position', ns) is not None else None
                quantity = point.find('ns:price.amount', ns).text if point.find('ns:price.amount', ns) is not None else None
                points.append({'position': position, 'quantity': quantity})

            series_data['periods'].append({
                'start': start,
                'end': end,
                'resolution': resolution,
                'points': points
            })

        timeseries_list.append(series_data)

    return timeseries_list


def get_data(timeseries_data):
    # Initialize a dictionary to store time series by bidding zones
    data_by_bidding_zone = {}

    for series in timeseries_data:
        # Extract the bidding zone (ensure the key exists in the parsed series)
        bidding_zone = series.get('in_Domain.mRID')  # Use .get() to avoid KeyError

        # Skip if bidding zone is not available
        if not bidding_zone:
            print("Warning: Bidding zone missing in the series.")
            continue

        # Process the periods in the time series
        for period in series['periods']:
            df = pd.DataFrame(period['points'])
            df['position'] = df['position'].astype(int)
            df['price.amount'] = df['price.amount'].astype(float)

            # Calculate datetime for each point
            start_time = pd.to_datetime(period['start'])
            resolution = pd.Timedelta(period['resolution'][2:].replace("M", "minutes").replace("H", "hours"))
            df['datetime'] = start_time + (df['position'] - 1) * resolution

            # Add day and interval columns
            df['day'] = df['datetime'].dt.tz_localize(None).dt.date  # Remove timezone
            interval_length = resolution.total_seconds() / 60
            df['interval'] = ((df['datetime'].dt.tz_localize(None) - pd.to_datetime(df['day'])) / pd.Timedelta(minutes=interval_length)).astype(int) + 1

            # If the bidding zone exists, append to the existing DataFrame
            if bidding_zone in data_by_bidding_zone:
                data_by_bidding_zone[bidding_zone] = pd.concat([data_by_bidding_zone[bidding_zone], df])
            else:
                # Otherwise, initialize with the current DataFrame
                data_by_bidding_zone[bidding_zone] = df

    # Sort DataFrames by datetime for each bidding zone
    for zone in data_by_bidding_zone:
        data_by_bidding_zone[zone] = data_by_bidding_zone[zone].sort_values(by='datetime')

    return data_by_bidding_zone


import xml.etree.ElementTree as ET
import pandas as pd

def get_namespace(element):
    # Extract the namespace from the XML root
    return element.tag[element.tag.find("{"):element.tag.find("}") + 1]

def get_unique_in_bidding_zones(xml_data):
    root = ET.fromstring(xml_data)
    namespace = get_namespace(root)  # Extract the namespace dynamically
    ns = {'ns': namespace[1:-1]}  # Format namespace for use in findall

    # Collect unique in_Domain.mRID values
    unique_in_bidding_zones = set()

    for time_series in root.findall('.//ns:TimeSeries', ns):
        in_bidding_zone = time_series.find('.//ns:in_Domain.mRID', ns)
        if in_bidding_zone is not None:
            unique_in_bidding_zones.add(in_bidding_zone.text)

    # Convert to a sorted list
    return sorted(unique_in_bidding_zones)

def create_zones_dict(xml_data):

    root = ET.fromstring(xml_data)
    namespace = get_namespace(root)  # Extract the namespace dynamically
    ns = {'ns': namespace[1:-1]}  # Format namespace for use in findall

    # Get the unique bidding zones
    unique_bidding_zones = get_unique_in_bidding_zones(xml_data)

    # Initialize the dictionary to hold DataFrames
    zones = {zone: [] for zone in unique_bidding_zones}

    # Loop through each TimeSeries
    for time_series in root.findall('.//ns:TimeSeries', ns):
        # Extract the in_Domain.mRID
        in_bidding_zone = time_series.find('.//ns:in_Domain.mRID', ns)
        if in_bidding_zone is not None:
            zone = in_bidding_zone.text

            # Extract periods and points
            for period in time_series.findall('.//ns:Period', ns):
                start = period.find('.//ns:timeInterval/ns:start', ns).text
                resolution = period.find('ns:resolution', ns).text

                points = []
                for point in period.findall('.//ns:Point', ns):
                    position = point.find('ns:position', ns).text
                    price = point.find('ns:price.amount', ns).text
                    points.append({'position': position, 'price.amount': price})

                # Create a DataFrame for this period
                df = pd.DataFrame(points)
                df['position'] = df['position'].astype(int)
                df['price.amount'] = df['price.amount'].astype(float)
                df['datetime'] = pd.to_datetime(start) + pd.to_timedelta(
                    (df['position'] - 1) * int(resolution[2:-1]), unit='m'
                )

                # Set datetime as the index
                df.reset_index(inplace=True)


                # Append the DataFrame to the appropriate zone
                zones[zone].append(df)

    # Combine DataFrames for each zone
    for zone in zones:
        zones[zone] = pd.concat(zones[zone]).sort_values(by='datetime', ascending=True).reset_index(drop=True)


    return zones

import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm  # For progress bar

def fetch_entsoe_continuous(document_type, process_type, start_date, end_date, bidding_zone):
    """
    Fetches ENTSO-E data in 2-day segments and concatenates the results.

    Parameters:
        - document_type (str): Document type for the API request.
        - process_type (str): Process type for the API request.
        - start_date (str): Start date in YYYYMMDDHHMM format.
        - end_date (str): End date in YYYYMMDDHHMM format.
        - bidding_zone (str): Bidding zone identifier.

    Returns:
        - pd.DataFrame: Concatenated DataFrame with continuous data.
    """

    start_dt = datetime.strptime(start_date, "%Y%m%d%H%M")
    end_dt = datetime.strptime(end_date, "%Y%m%d%H%M")
    delta = timedelta(days=2)

    all_dataframes = []
    total_segments = (end_dt - start_dt) // delta + 1

    for i in tqdm(range(total_segments), desc="Fetching Data Progress", unit="segment"):
        segment_start = start_dt + i * delta
        segment_end = min(segment_start + delta, end_dt)

        segment_start_str = segment_start.strftime("%Y%m%d%H%M")
        segment_end_str = segment_end.strftime("%Y%m%d%H%M")

        df_segment = fetch_entsoe_data(document_type, process_type, segment_start_str, segment_end_str, bidding_zone)

        df_index = create_zones_dict(df_segment)[bidding_zone]

        all_dataframes.append(df_index)

    final_df = pd.concat(all_dataframes, ignore_index=True)

    # Rename the 'datetime' column to 'timestamp'
    final_df.rename(columns={'datetime': 'timestamp'}, inplace=True)
    final_df.rename(columns={'price.amount': 'price'}, inplace=True)

    return final_df



import matplotlib.pyplot as plt
import pandas as pd

def plot_price_trends(a,start_date, end_date, b=None):
    """
    Plots electricity price trends over time.
    
    Parameters:
    - a (pd.DataFrame): DataFrame containing 'datetime' and 'price.amount' for Day-Ahead prices.
    - b (pd.DataFrame, optional): DataFrame containing 'datetime' and 'price.amount' for Intraday prices.
    """
    
    plt.figure(figsize=(10, 6))
    
    # Ensure 'datetime' is a proper datetime type
    a['timestamp'] = pd.to_datetime(a['timestamp'])
    
    # Plot Day-Ahead prices
    plt.plot(a['timestamp'], a['price.amount'], label='Price Amount DA', color='b')
    
    # Plot Intraday prices if provided
    if b is not None:
        b['timestamp'] = pd.to_datetime(b['timestamp'])
        plt.plot(b['timestamp'], b['price.amount'], label='Price Amount Intra', color='y')
    
    # Formatting
    plt.title('Price Amount Over Time')
    plt.xlabel('Datetime')
    plt.ylabel('Price (EUR/MWh)')
    plt.grid(True)
    plt.xticks(rotation=45)  # Rotate x-axis labels for readability
    plt.tight_layout()
    
    # Add vertical dashed lines for every midnight and noon
    for timestamp in a['timestamp']:
        if timestamp.hour == 0:  # Midnight
            plt.axvline(x=timestamp, linestyle='--', color='red', alpha=0.7, 
                        label='Midnight' if 'Midnight' not in plt.gca().get_legend_handles_labels()[1] else "")
        elif timestamp.hour == 12:  # Noon
            plt.axvline(x=timestamp, linestyle='--', color='blue', alpha=0.7, 
                        label='Noon' if 'Noon' not in plt.gca().get_legend_handles_labels()[1] else "")
            

    start_date = pd.Timestamp(start_date)  # Set your desired start date
    end_date = pd.Timestamp(end_date)  # Set your desired end date

    plt.xlim(start_date, end_date)
    
    plt.legend(title='Legend', bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.show()




