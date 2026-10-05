import pytest
from routing.services import optimize_fuel

class MockStation:
    def __init__(self, opis_id, name, city, state):
        self.opis_id = opis_id
        self.name = name
        self.city = city
        self.state = state

def test_greedy_fuel_optimization_chooses_cheaper_station():
    """
    Test that if a cheaper station is within range, the algorithm 
    only buys enough fuel to reach it.
    """
    stations = [
        {
            'station': MockStation(1, "Expensive Start", "CityA", "TX"),
            'dist_from_start': 0.0,
            'price': 4.00
        },
        {
            'station': MockStation(2, "Cheaper Next", "CityB", "TX"),
            'dist_from_start': 100.0,
            'price': 2.00
        },
        {
            'station': MockStation(3, "Destination", "CityC", "TX"),
            'dist_from_start': 300.0,
            'price': 2.50
        }
    ]
    
    stops, total_cost = optimize_fuel(stations, 300.0)
    
    # Assert we only bought enough at station 1 to reach station 2
    # Distance is 100 miles, so we need 100 / 10 = 10 gallons.
    assert stops[0]['station_id'] == 1
    assert stops[0]['gallons_bought'] == 10.0
    
    # Assert we filled up at station 2 to reach destination
    # Distance from 2 to destination is 200 miles, need 20 gallons.
    assert stops[1]['station_id'] == 2
    assert stops[1]['gallons_bought'] == 20.0
    
    # Assert total cost: (10 gal * $4) + (20 gal * $2) = $40 + $40 = $80
    assert total_cost == 80.0

def test_greedy_fuel_optimization_expensive_ahead():
    """
    Test that if all stations ahead are more expensive, 
    we fill the tank completely at the current station.
    """
    stations = [
        {
            'station': MockStation(1, "Cheap Start", "CityA", "TX"),
            'dist_from_start': 0.0,
            'price': 2.00
        },
        {
            'station': MockStation(2, "Expensive Next", "CityB", "TX"),
            'dist_from_start': 200.0,
            'price': 5.00
        }
    ]
    
    stops, total_cost = optimize_fuel(stations, 400.0)
    
    # We should buy the absolute maximum (50 gallons) at the cheap start
    assert stops[0]['station_id'] == 1
    assert stops[0]['gallons_bought'] == 50.0
