import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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
        print(f"Data {document_type}_{process_type} Retrieved Successfully")
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
            'mRID': time_series.find('ns:mRID', ns).text,
            'businessType': time_series.find('ns:businessType', ns).text,
            'biddingZone': time_series.find('.//ns:outBiddingZone_Domain.mRID', ns).text,
            'unit': time_series.find('.//ns:quantity_Measure_Unit.name', ns).text,
            'curveType': time_series.find('ns:curveType', ns).text,
            'periods': []
        }
        
        # Parse periods and points
        for period in time_series.findall('.//ns:Period', ns):
            start = period.find('.//ns:timeInterval/ns:start', ns).text
            end = period.find('.//ns:timeInterval/ns:end', ns).text
            resolution = period.find('ns:resolution', ns).text
            
            points = []
            for point in period.findall('.//ns:Point', ns):
                position = point.find('ns:position', ns).text
                quantity = point.find('ns:quantity', ns).text
                points.append({'position': position, 'quantity': quantity})
            
            series_data['periods'].append({
                'start': start,
                'end': end,
                'resolution': resolution,
                'points': points
            })
        
        timeseries_list.append(series_data)
    
    return timeseries_list


def parse_timeseries_with_namespace_price(xml_data):
    root = ET.fromstring(xml_data)
    namespace = get_namespace(root)  # Extract namespace dynamically
    ns = {'ns': namespace[1:-1]}  # Format namespace for findall

    timeseries_list = []

    for time_series in root.findall('.//ns:TimeSeries', ns):
        series_data = {
            'mRID': time_series.find('ns:mRID', ns).text,
            'auctionType': time_series.find('ns:auction.type', ns).text,
            'businessType': time_series.find('ns:businessType', ns).text,
            'in_Domain': time_series.find('.//ns:in_Domain.mRID', ns).text,
            'out_Domain': time_series.find('.//ns:out_Domain.mRID', ns).text,
            'currency': time_series.find('.//ns:currency_Unit.name', ns).text,
            'price_unit': time_series.find('.//ns:price_Measure_Unit.name', ns).text,
            'curveType': time_series.find('ns:curveType', ns).text,
            'periods': []
        }
        
        # Parse periods and points
        for period in time_series.findall('.//ns:Period', ns):
            start = period.find('.//ns:timeInterval/ns:start', ns).text
            end = period.find('.//ns:timeInterval/ns:end', ns).text
            resolution = period.find('ns:resolution', ns).text
            
            points = []
            for point in period.findall('.//ns:Point', ns):
                position = point.find('ns:position', ns).text
                price = point.find('ns:price.amount', ns).text  # Adjusted to extract price
                points.append({'position': position, 'price': price})
            
            series_data['periods'].append({
                'start': start,
                'end': end,
                'resolution': resolution,
                'points': points
            })
        
        timeseries_list.append(series_data)
    
    return timeseries_list


def get_data(timeseries_data):
    # Collect data from all time series
    all_data = []

    for series in timeseries_data:
        for period in series['periods']:
            df = pd.DataFrame(period['points'])
            df['position'] = df['position'].astype(int)
            df['quantity'] = df['quantity'].astype(float)

            # Calculate datetime for each point
            start_time = pd.to_datetime(period['start'])
            df['datetime'] = start_time + pd.to_timedelta((df['position'] - 1) * 15, unit='m')

            # Add day and interval columns
            df['day'] = df['datetime'].dt.tz_localize(None).dt.date  # Remove timezone
            df['interval'] = ((df['datetime'].dt.tz_localize(None) - pd.to_datetime(df['day'])) / pd.Timedelta(minutes=15)).astype(int) + 1

            # Append the data for this period
            all_data.append(df)

    # Concatenate all data into one DataFrame
    full_df = pd.concat(all_data).sort_values(by='datetime')

    return full_df


def get_data_price(timeseries_data):
    # Collect data from all time series
    all_data = []

    for series in timeseries_data:
        for period in series['periods']:
            df = pd.DataFrame(period['points'])
            df['position'] = df['position'].astype(int)
            df['price'] = df['price'].astype(float)  # Price instead of quantity

            # Calculate datetime for each point (hourly intervals)
            start_time = pd.to_datetime(period['start'])
            df['datetime'] = start_time + pd.to_timedelta((df['position'] - 1), unit='h')

            # Add day and interval columns
            df['day'] = df['datetime'].dt.tz_localize(None).dt.date  # Remove timezone
            df['interval'] = ((df['datetime'].dt.tz_localize(None) - pd.to_datetime(df['day'])) / pd.Timedelta(hours=1)).astype(int) + 1

            # Append the data for this period
            all_data.append(df)

    # Concatenate all data into one DataFrame
    full_df = pd.concat(all_data).sort_values(by='datetime')
    return full_df


def fetch_and_process_entsoe_data(document_type, process_type, start, end, bidding_zone='10YNL----------L'):
    # Fetch Data using existing fetch function
    xml_data = fetch_entsoe_data(
        document_type=document_type,
        process_type=process_type,
        start=start,
        end=end,
        bidding_zone=bidding_zone
    )
    
    # If no data is retrieved, return None
    if xml_data is None:
        return None
    
    # Parse XML Data
    parsed_data = parse_timeseries_with_namespace(xml_data)
    
    # Extract Data into DataFrame
    processed_data = get_data(parsed_data)

    # Rename the 'datetime' column to 'timestamp'
    processed_data.rename(columns={'datetime': 'timestamp'}, inplace=True)

    

    
    return processed_data






