import csv
import time
import requests
import os

# --- Configuration ---
INPUT_CSV = 'data/fuel-prices-for-be-assessment.csv'
OUTPUT_CSV = 'data/fuel_geocoded.csv'
DELAY_BETWEEN_REQUESTS = 0.5
ID_COLUMN = 'OPIS Truckstop ID'
FLUSH_INTERVAL = 20

# State mapping for strict accuracy validation
STATE_ABBREV_TO_NAME = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}

def geocode_city_state(city, state_abbrev):
    """
    Uses the free Open-Meteo Geocoding API
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        'name': city,
        'count': 10,
        'format': 'json'
    }
    
    expected_state_name = STATE_ABBREV_TO_NAME.get(state_abbrev.upper())
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if 'results' in data:
            for result in data['results']:
                # Validation 1: Must be in the USA
                if result.get('country_code') == 'US':
                    returned_state = result.get('admin1', '')
                    
                    # Validation 2: Must match the exact State
                    if expected_state_name and expected_state_name.lower() in returned_state.lower():
                        lat = float(result['latitude'])
                        lon = float(result['longitude'])
                        
                        # Validation 3: Rough USA Bounding Box check
                        if (24.0 <= lat <= 50.0) and (-125.0 <= lon <= -66.0):
                            return lat, lon
                            
            print(f"  [Warning] Found city '{city}', but it did not match state '{state_abbrev}'")
                        
    except requests.exceptions.RequestException as e:
        print(f"  [Error] API Request failed for {city}, {state_abbrev}: {e}")
        
    return None, None

def get_processed_ids():
    processed = set()
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if row.get(ID_COLUMN):
                    processed.add(row[ID_COLUMN])
    return processed

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: Could not find '{INPUT_CSV}'. Please ensure the file is in the same directory.")
        return

    processed_ids = get_processed_ids()
    print(f"Found {len(processed_ids)} already processed records. Resuming...")
    
    with open(INPUT_CSV, mode='r', encoding='utf-8-sig') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['Latitude', 'Longitude']
        
        file_mode = 'a' if os.path.exists(OUTPUT_CSV) else 'w'
        
        with open(OUTPUT_CSV, mode=file_mode, encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            
            if file_mode == 'w':
                writer.writeheader()
            
            records_since_last_flush = 0
            
            for index, row in enumerate(reader):
                row_id = row.get(ID_COLUMN)
                
                if row_id in processed_ids:
                    continue
                
                city = row.get('City', '').strip()
                state = row.get('State', '').strip()
                name = row.get('Truckstop Name', '').strip()
                
                print(f"Processing: {name} in {city}, {state}...")
                
                lat, lon = geocode_city_state(city, state)
                
                if lat and lon:
                    row['Latitude'] = lat
                    row['Longitude'] = lon
                else:
                    row['Latitude'] = ''
                    row['Longitude'] = ''
                
                writer.writerow(row)
                processed_ids.add(row_id)
                records_since_last_flush += 1
                
                if records_since_last_flush >= FLUSH_INTERVAL:
                    outfile.flush()
                    print(f"  [System] Flushed {FLUSH_INTERVAL} new records to disk.")
                    records_since_last_flush = 0
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
            
            if records_since_last_flush > 0:
                outfile.flush()
                print(f"  [System] Flushed final {records_since_last_flush} records to disk.")

    print(f"\nFinished! All data processed and saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
