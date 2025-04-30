import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import matplotlib.pyplot as plt

fuel_types = {
        'B01': 'Biomass',
        'B02': 'Fossil Brown Coal/Lignite',
        'B03': 'Fossil Coal-derived Gas',
        'B04': 'Fossil Gas',
        'B05': 'Fossil Hard Coal',
        'B06': 'Fossil Oil',
        'B07': 'Fossil Oil Shale',
        'B08': 'Fossil Peat',
        'B09': 'Geothermal',
        'B10': 'Hydro Pumped Storage',
        'B11': 'Hydro Run-of-river and Poundage',
        'B12': 'Hydro Water Reservoir',
        'B13': 'Marine',
        'B14': 'Nuclear',
        'B15': 'Other Renewable',
        'B16': 'Solar',
        'B17': 'Waste',
        'B18': 'Wind Offshore',
        'B19': 'Wind Onshore',
        'B20': 'Other',
        'B25': 'Energy Storage'
    }


# Function to extract the namespace from an XML element
def get_namespace(element):
    match = re.match(r'\{.*\}', element.tag)
    return match.group(0) if match else ''

# Function to fetch data from the ENTSO-E API
def fetch_entsoe_data(document_type, process_type, start, end, bidding_zone='10YNL----------L'):

    API_TOKEN = 'xx'

    BASE_URL = 'https://web-api.tp.entsoe.eu/api'

    params = {
        'securityToken': API_TOKEN,
        'documentType': document_type,
        'processType': process_type,
        'in_Domain': bidding_zone,
        'periodStart': start,
        'periodEnd': end
    }

    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        print(f"Data {document_type}_{process_type} Retrieved Successfully")
        return response.text
        

    else:
        print(f"Error: {response.status_code}")
        return None

# Function to parse the XML data and extract time series information
def parse_timeseries_with_namespace(xml_data):
    root = ET.fromstring(xml_data)
    namespace = get_namespace(root)
    ns = {'ns': namespace[1:-1]}  # Remove curly braces

    timeseries_list = []

    for time_series in root.findall('.//ns:TimeSeries', ns):
        series_data = {
            'mRID': time_series.find('ns:mRID', ns).text,
            'businessType': time_series.find('ns:businessType', ns).text,
            'psrType': time_series.find('.//ns:psrType', ns).text,
            'periods': []
        }

        for period in time_series.findall('.//ns:Period', ns):
            start = period.find('.//ns:timeInterval/ns:start', ns).text
            end = period.find('.//ns:timeInterval/ns:end', ns).text
            resolution = period.find('ns:resolution', ns).text

            points = []
            for point in period.findall('.//ns:Point', ns):
                position = int(point.find('ns:position', ns).text)
                quantity = float(point.find('ns:quantity', ns).text)
                points.append({'position': position, 'quantity': quantity})

            series_data['periods'].append({
                'start': start,
                'end': end,
                'resolution': resolution,
                'points': points
            })

        timeseries_list.append(series_data)

    return timeseries_list

# Function to convert the parsed time series data into a DataFrame
def timeseries_to_dataframe(timeseries_data, start_time=None, end_time=None):
    all_data = []

    for series in timeseries_data:
        for period in series['periods']:
            start_time_period = pd.to_datetime(period['start'])
            resolution = pd.Timedelta(period['resolution'])

            for point in period['points']:
                timestamp = start_time_period + (point['position'] - 1) * resolution
                all_data.append({
                    'timestamp': timestamp,
                    'psrType': series['psrType'],
                    'quantity': point['quantity']
                })

    df = pd.DataFrame(all_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Map PSR types to readable names
    df = map_psr_type_labels(df)

        # Set start and end time to min and max of the DataFrame if not provided
    if start_time is None:
        start_time = df['timestamp'].min()
    if end_time is None:
        end_time = df['timestamp'].max()

    # Apply time filter
    resampled_df = df[
        (df['timestamp'] > start_time) &
        (df['timestamp'] < end_time)
    ]

    # Calculate total generation by summing all production types
    total_generation_df = df.groupby('timestamp')['quantity'].sum().reset_index()
    total_generation_df.rename(columns={'quantity': 'total_generation_grouped'}, inplace=True)

    # Aggregate to remove duplicates
    filtered_df = df.groupby(['Production Type', 'timestamp']).sum().reset_index()

    # Ensure proper dtypes for all columns
    filtered_df = filtered_df.infer_objects(copy=False)

    # Set timestamp as index for resampling
    filtered_df.set_index('timestamp', inplace=True)



    # Reset index for plotting
    if 'Production Type' in df.columns:
        resampled_df = df.drop(columns=['Production Type'])

    resampled_df.reset_index(inplace=True)



    return  resampled_df, total_generation_df


def map_psr_type_labels(df):
    psr_type_mapping = {
        'B01': 'Biomass',
        'B02': 'Fossil Brown Coal/Lignite',
        'B03': 'Fossil Coal-derived Gas',
        'B04': 'Fossil Gas',
        'B05': 'Fossil Hard Coal',
        'B06': 'Fossil Oil',
        'B07': 'Fossil Oil Shale',
        'B08': 'Fossil Peat',
        'B09': 'Geothermal',
        'B10': 'Hydro Pumped Storage',
        'B11': 'Hydro Run-of-river and Poundage',
        'B12': 'Hydro Water Reservoir',
        'B13': 'Marine',
        'B14': 'Nuclear',
        'B15': 'Other Renewable',
        'B16': 'Solar',
        'B17': 'Waste',
        'B18': 'Wind Offshore',
        'B19': 'Wind Onshore',
        'B20': 'Other',
        'B25': 'Energy Storage'
    }

    # Map the codes to readable labels
    df['Production Type'] = df['psrType'].map(psr_type_mapping).fillna(df['psrType'])
    return df


def plot_selected_types(df, start_day, start_month, start_year, 
                        end_day, end_month, end_year, selected_types):
    """
    Plots the generation data for selected production types over time, with time filtering.

    Parameters:
    df (pandas.DataFrame): A DataFrame containing 'timestamp', 'psrType', and 'quantity' columns.
    start_day (int): Start day.
    start_month (int): Start month.
    start_year (int): Start year.
    end_day (int): End day.
    end_month (int): End month.
    end_year (int): End year.
    """


    # Ensure timestamp is in datetime format
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Remove timezone (convert to tz-naive)
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)

    # Create start and end datetime strings
    start_time = f"{start_year:04d}-{start_month:02d}-{start_day:02d} 00:00:00"
    end_time = f"{end_year:04d}-{end_month:02d}-{end_day:02d} 23:59:59"

    start_time = pd.to_datetime(start_time)
    end_time = pd.to_datetime(end_time)

    # Filter the DataFrame for the selected types
    filtered_df = df[df['Production Type'].isin(selected_types)]

    # Apply time filter
    filtered_df = filtered_df[
        (filtered_df['timestamp'] >= start_time) &
        (filtered_df['timestamp'] <= end_time)
    ]

        # Calculate total generation by summing all production types
    total_generation_df = filtered_df.groupby('timestamp')['quantity'].sum().reset_index()
    total_generation_df.rename(columns={'quantity': 'Total Generation (MW)'}, inplace=True)


    # Aggregate to remove duplicates
    filtered_df = filtered_df.groupby(['Production Type', 'timestamp']).sum().reset_index()

    # Set timestamp as index for resampling
    filtered_df.set_index('timestamp', inplace=True)

    # Resample and interpolate for each production type
    resampled_df = filtered_df.groupby('Production Type').resample('15min').interpolate().copy()


        # Reset index for plotting
    if 'Production Type' in resampled_df.columns:
        resampled_df = resampled_df.drop(columns=['Production Type'])

    resampled_df.reset_index(inplace=True)

    # Plot each production type
    plt.figure(figsize=(12, 6))
    
    for psr_type, group in resampled_df.groupby('Production Type'):
        plt.plot(group['timestamp'], group['quantity'], label=psr_type)

        # Plot total generation line
    plt.plot(total_generation_df['timestamp'], total_generation_df['Total Generation (MW)'], 
             color='black', linestyle='--', linewidth=2, label='Total Generation')


    plt.xlabel('Time')
    plt.ylabel('Generation (MW)')
    plt.title('Generation Over Time by Selected Production Types')
    # plt.legend(title='Production Type')
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def retrieve_generation_data(document_type, process_type, start, end):
    # Fetch data
    xml_data = fetch_entsoe_data(document_type, process_type, start, end)

    if xml_data:
        # Parse XML data
        timeseries_data = parse_timeseries_with_namespace(xml_data)

        # Convert to DataFrame
        data = timeseries_to_dataframe(timeseries_data)
    
    return data


def get_generation_data(start, end):

    df, totals = retrieve_generation_data('A75', 'A16', start, end)
    df = map_psr_type_labels(df)

    pivoted = df.pivot_table(
        index='timestamp',
        columns='Production Type',
        values='quantity',
        aggfunc='sum'
    )

    # Remove the "Production Type" name on the columns axis
    pivoted.columns.name = None

    # Now put 'timestamp' back as a normal column, but DON'T create an 'index' column
    pivoted.reset_index(drop=False, inplace=True)  # 'timestamp' becomes a column
    #    ^ drop=False means we keep the "timestamp" column. 
    #      There's no separate "index" because the pivoted index was just 'timestamp'.

    # If you *still* see an "index" column after this, you can drop it:
    if 'index' in pivoted.columns:
        pivoted.drop(columns=['index'], inplace=True)

    # Assuming you already have your dataframes: totals and pivoted
    merged_df = pd.merge(totals, pivoted, on='timestamp', how='outer')

    # Sorting by timestamp to maintain order
    merged_df = merged_df.sort_values(by='timestamp')

    merged_df['Total_generation'] = 0

    for fuel_type in fuel_types.keys():

        type = fuel_types[fuel_type]

        if type in merged_df.columns.to_list():

            merged_df['Total_generation'] =  merged_df['Total_generation'] + merged_df[type]
        
    # Optional: rename columns to avoid spaces, etc.
    merged_df.columns = merged_df.columns.str.lower().str.replace(" ", "_")

    merged_df.rename(columns={"hydro_run-of-river_and_poundage": "hydro_run_of_river_and_poundage"}, inplace=True)

    merged_df['total_wind'] = merged_df['wind_offshore'] + merged_df['wind_onshore']



    return merged_df

