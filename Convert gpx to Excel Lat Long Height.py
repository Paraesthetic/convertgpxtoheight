import subprocess
import sys
import pkg_resources

# Function to check and install required packages
def install_packages():
    required = {'gpxpy', 'pandas', 'numpy', 'requests', 'geopy', 'scipy', 'tk', 'openpyxl'}
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = required - installed

    if missing:
        print(f"Installing missing packages: {missing}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

install_packages()

import gpxpy
import pandas as pd
import numpy as np
import requests
from geopy.distance import geodesic
from scipy.interpolate import interp1d
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename

# Function to parse GPX and get coordinates
def parse_gpx(gpx_file_path):
    with open(gpx_file_path, 'r') as gpx_file:
        gpx = gpxpy.parse(gpx_file)
        coords = [(point.latitude, point.longitude) for track in gpx.tracks for segment in track.segments for point in segment.points]
    return coords

# Function to get elevation data from Google Maps API
def get_elevation_data_google(coords, api_key):
    elevations = []
    base_url = "https://maps.googleapis.com/maps/api/elevation/json"

    for i in range(0, len(coords), 512):
        locations = '|'.join([f"{lat},{lon}" for lat, lon in coords[i:i+512]])
        url = f"{base_url}?locations={locations}&key={api_key}"
        response = requests.get(url)
        results = response.json().get('results', [])
        
        for result in results:
            elevations.append(result['elevation'])

    return elevations

# Function to interpolate heights and coordinates every meter
def interpolate_heights_and_coords(coords, elevations):
    distances = [0]
    for i in range(1, len(coords)):
        distances.append(distances[-1] + geodesic(coords[i-1], coords[i]).meters)

    new_distances = np.arange(0, distances[-1], 1)
    
    f_interp = interp1d(distances, elevations, kind='linear')
    new_heights = f_interp(new_distances)

    f_interp_lat = interp1d(distances, [coord[0] for coord in coords], kind='linear')
    f_interp_lon = interp1d(distances, [coord[1] for coord in coords], kind='linear')
    new_lats = f_interp_lat(new_distances)
    new_lons = f_interp_lon(new_distances)

    new_coords = [(lat, lon) for lat, lon in zip(new_lats, new_lons)]

    return new_distances, new_heights, new_coords

# Main function to execute the entire process
def main(google_api_key):
    # Show a file dialog to select the GPX file
    Tk().withdraw()  # We don't want a full GUI, so keep the root window from appearing
    gpx_file_path = askopenfilename(filetypes=[("GPX files", "*.gpx")])
    
    if not gpx_file_path:
        print("No file selected.")
        return

    # Show a save dialog to name the output Excel file
    output_excel_path = asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
    
    if not output_excel_path:
        print("No output file name provided.")
        return

    coords = parse_gpx(gpx_file_path)
    elevations = get_elevation_data_google(coords, google_api_key)
    
    if not elevations:
        print("No elevation data found from Google Maps API.")
        return
    
    distances, heights, interpolated_coords = interpolate_heights_and_coords(coords, elevations)

    df = pd.DataFrame({
        'Distance (m)': distances, 
        'Height (m)': heights,
        'Latitude': [coord[0] for coord in interpolated_coords],
        'Longitude': [coord[1] for coord in interpolated_coords]
    })
    df.to_excel(output_excel_path, index=False)
    return df

# Running the script
google_api_key = 'AIzaSyD42_DLNyG7X9R2NfpQJ3noCslIALX_A4I'  # Update this with your Google API key
df_result = main(google_api_key)
if df_result is not None:
    print(df_result.head())  # Displaying the first few rows of the resulting DataFrame
