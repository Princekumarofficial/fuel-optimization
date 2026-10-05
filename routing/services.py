import math
import urllib.request
import json
from routing.models import FuelStation
from django.core.cache import cache

# Constants
MAX_RANGE_MILES = 500.0
MPG = 10.0
MAX_GALLONS = MAX_RANGE_MILES / MPG

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in miles.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 3956 # Radius of earth in miles
    return c * r

def fetch_routes(start_lon, start_lat, end_lon, end_lat):
    """
    Fetches up to 3 alternative routes from OSRM public API.
    Returns a list of tuples: (geometry, total_distance_miles).
    """
    # Ask for up to 3 alternatives in a single API call!
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson&alternatives=3"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'FuelOptimizerApp/1.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        
        if data['code'] != 'Ok':
            raise ValueError("Could not find a valid route between these locations.")
            
        parsed_routes = []
        for route in data['routes']:
            total_distance_miles = route['distance'] / 1609.34
            geometry = route['geometry']
            parsed_routes.append((geometry, total_distance_miles))
            
        return parsed_routes

def find_stations_along_route(geometry):
    """
    Finds stations near the route and calculates their distance from the start.
    """
    coords = geometry['coordinates']
    if not coords:
        return []
        
    route_points = []
    cumulative_dist = 0.0
    for i in range(len(coords)):
        lon, lat = coords[i]
        if i > 0:
            prev_lon, prev_lat = coords[i-1]
            cumulative_dist += haversine(prev_lat, prev_lon, lat, lon)
        route_points.append({'lat': lat, 'lon': lon, 'dist_from_start': cumulative_dist})
        
    lats = [p['lat'] for p in route_points]
    lons = [p['lon'] for p in route_points]
    min_lat, max_lat = min(lats) - 0.5, max(lats) + 0.5
    min_lon, max_lon = min(lons) - 0.5, max(lons) + 0.5
    
    candidate_stations = FuelStation.objects.filter(
        latitude__range=(min_lat, max_lat),
        longitude__range=(min_lon, max_lon)
    )
    
    mapped_stations = []
    for station in candidate_stations:
        min_dist_to_route = float('inf')
        dist_from_start = 0.0
        
        for point in route_points:
            dist = haversine(station.latitude, station.longitude, point['lat'], point['lon'])
            if dist < min_dist_to_route:
                min_dist_to_route = dist
                dist_from_start = point['dist_from_start']
                
        if min_dist_to_route <= 5.0:
            mapped_stations.append({
                'station': station,
                'dist_from_start': dist_from_start,
                'price': station.retail_price
            })
            
    mapped_stations.sort(key=lambda x: x['dist_from_start'])
    return mapped_stations

def optimize_fuel(stations, total_distance):
    """
    The Greedy Fuel Optimization Algorithm.
    """
    stops = []
    current_fuel = 0.0
    total_cost = 0.0
    
    stations.append({
        'station': type('obj', (object,), {'name': 'Destination', 'opis_id': -1, 'city': 'End', 'state': '', 'latitude': None, 'longitude': None}),
        'dist_from_start': total_distance,
        'price': 0.0
    })
    
    i = 0
    while i < len(stations):
        current_station = stations[i]
        
        if current_station['dist_from_start'] >= total_distance:
            break
            
        if i + 1 < len(stations):
            distance_to_next = stations[i+1]['dist_from_start'] - current_station['dist_from_start']
            if distance_to_next > MAX_RANGE_MILES:
                raise ValueError(f"Route impossible. Gap of {distance_to_next:.1f} miles exceeds vehicle range.")
        
        reachable_stations = []
        for j in range(i + 1, len(stations)):
            if stations[j]['dist_from_start'] - current_station['dist_from_start'] <= MAX_RANGE_MILES:
                reachable_stations.append((j, stations[j]))
            else:
                break
                
        if not reachable_stations:
             raise ValueError("Cannot reach the next station.")
             
        next_stop_idx = None
        for j, stat in reachable_stations:
            if stat['price'] < current_station['price']:
                next_stop_idx = j
                break
                
        if next_stop_idx is not None:
            # Case 1: Cheaper station ahead
            target_station = stations[next_stop_idx]
            dist_to_target = target_station['dist_from_start'] - current_station['dist_from_start']
            gallons_needed = dist_to_target / MPG
            
            gallons_to_buy = max(0, gallons_needed - current_fuel)
            if gallons_to_buy > 0:
                cost = gallons_to_buy * current_station['price']
                total_cost += cost
                stops.append({
                    'station_id': current_station['station'].opis_id,
                    'name': current_station['station'].name,
                    'city': current_station['station'].city,
                    'state': current_station['station'].state,
                    'latitude': getattr(current_station['station'], 'latitude', None),
                    'longitude': getattr(current_station['station'], 'longitude', None),
                    'price': current_station['price'],
                    'gallons_bought': round(gallons_to_buy, 2),
                    'cost': round(cost, 2),
                    'distance_from_start': round(current_station['dist_from_start'], 2)
                })
                current_fuel += gallons_to_buy
                
            current_fuel -= (dist_to_target / MPG)
            i = next_stop_idx
            
        else:
            # Case 2: All stations ahead are more expensive
            gallons_to_buy = MAX_GALLONS - current_fuel
            cost = gallons_to_buy * current_station['price']
            total_cost += cost
            
            if gallons_to_buy > 0:
                stops.append({
                    'station_id': current_station['station'].opis_id,
                    'name': current_station['station'].name,
                    'city': current_station['station'].city,
                    'state': current_station['station'].state,
                    'latitude': getattr(current_station['station'], 'latitude', None),
                    'longitude': getattr(current_station['station'], 'longitude', None),
                    'price': current_station['price'],
                    'gallons_bought': round(gallons_to_buy, 2),
                    'cost': round(cost, 2),
                    'distance_from_start': round(current_station['dist_from_start'], 2)
                })
            
            current_fuel = MAX_GALLONS
            
            cheapest_j = min(reachable_stations, key=lambda x: x[1]['price'])[0]
            target_station = stations[cheapest_j]
            dist_to_target = target_station['dist_from_start'] - current_station['dist_from_start']
            current_fuel -= (dist_to_target / MPG)
            i = cheapest_j
            
    return stops, total_cost

def calculate_optimized_trip(start_lon, start_lat, end_lon, end_lat):
    """
    Main orchestration function. Evaluates multiple paths to find the absolute cheapest!
    """
    cache_key = f"route_{round(start_lon,3)}_{round(start_lat,3)}_{round(end_lon,3)}_{round(end_lat,3)}"
    
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
        
    routes = fetch_routes(start_lon, start_lat, end_lon, end_lat)
    
    best_result = None
    min_cost = float('inf')
    
    for geometry, total_distance in routes:
        try:
            mapped_stations = find_stations_along_route(geometry)
            if not mapped_stations:
                continue
                
            stops, total_cost = optimize_fuel(mapped_stations, total_distance)
            
            # If this route is cheaper than our previous best, save it!
            if total_cost < min_cost:
                min_cost = total_cost
                best_result = {
                    'route_geometry': geometry,
                    'total_distance_miles': round(total_distance, 2),
                    'total_cost': round(total_cost, 2),
                    'fuel_stops': stops
                }
        except ValueError:
            continue
            
    if not best_result:
        raise ValueError("Could not find a route with reachable fuel stations.")
    
    cache.set(cache_key, best_result, timeout=60*60*24)
    
    return best_result
