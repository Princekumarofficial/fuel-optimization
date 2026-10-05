# 🗺️ Fuel Optimization Engine

An elegant, high-performance Django REST API that calculates the absolute most cost-effective fueling strategy for a road trip across the USA.

This project goes beyond simple straight-line routing. It evaluates **multiple physical road trip paths**, filters for gas stations strictly within a 5-mile radius of the highway, and uses a mathematical **Greedy Optimization Algorithm** to determine exactly where to stop and how much fuel to buy to minimize total cost.

---

## ✨ Architectural Highlights & Engineering Decisions

* **Multi-Path Evaluation:** The system does not just accept the first route it finds. It requests up to 3 alternative physical routes from the mapping API, runs the optimization algorithm on all of them, and returns the path with the lowest macro-economic fuel cost.
* **The Optimization Algorithm:** To solve the 500-mile range constraint, I deliberately avoided graph-search algorithms like Dijkstra (which suffer from state-space explosion when dealing with continuous variables like fuel capacity). Instead, the system uses a **Greedy Algorithm** running in $O(N)$ time. By mathematically looking ahead 500 miles and determining whether to buy just enough to reach a cheaper station, or fill the tank completely, the algorithm guarantees global optimality.
* **Spatial Mathematics:** Stations aren't chosen by simple straight-line distance. The API parses the actual GeoJSON Polyline of the highway, maps the stations to the exact curves of the road using the Haversine formula, and discards any station that is more than a 5-mile detour from the highway exit.
* **Caching (Redis Ready):** To strictly minimize calls to the external routing API, the orchestration engine is wrapped in a Django cache layer. Coordinates are rounded to a 100-meter radius to create stable cache keys, allowing identical trips to be served instantly in $O(1)$ time.
* **Idempotent Data Ingestion:** The raw CSV data is processed by a custom, resumable Python script that safely falls back to city-level geocoding to bypass the strict anti-bot measures of free geocoding APIs.
* **Frontend Visualization:** Includes a lightweight, vanilla JS + Leaflet.js frontend to visually demonstrate the API's routing and map markers without the overhead of a heavy SPA framework.

---

## 🚀 Quickstart (Docker Development)

The easiest way to review this code is via the provided Docker Compose development environment, which spins up the Django API and a dedicated Redis cache container.

**1. Start the Containers**

```bash
docker-compose -f docker-compose.dev.yml up --build
```

**2. Initialize the Database (In a separate terminal)**

```bash
docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
```

**3. Load the Fuel Data**

```bash
docker-compose -f docker-compose.dev.yml exec web python manage.py load_fuel_data data/fuel_geocoded.csv
```

**4. View the Map Application**
Open your browser to `http://localhost:8000/` to use the interactive map visualization.

---

## 📡 API Documentation

### `POST /api/optimize-route/`

Calculates the optimal route and fuel stops based on start and end coordinates.

**Request Body:**

```json
{
    "start_lon": -87.6298,
    "start_lat": 41.8781,
    "end_lon": -96.7970,
    "end_lat": 32.7767
}
```

**Success Response (200 OK):**

```json
{
    "route_geometry": {
        "type": "LineString",
        "coordinates": [
            [-87.6298, 41.8781],
            [-87.6310, 41.8770]
        ]
    },
    "total_distance_miles": 925.4,
    "total_cost": 185.20,
    "fuel_stops": [
        {
            "station_id": 1243,
            "name": "PILOT TRAVEL CENTER",
            "city": "Springfield",
            "state": "IL",
            "latitude": 39.7817,
            "longitude": -89.6501,
            "price": 2.99,
            "gallons_bought": 25.5,
            "cost": 76.24,
            "distance_from_start": 205.0
        }
    ]
}
```

**Error Responses:**

* `400 Bad Request`: If the route is impossible (e.g., a 600-mile gap without gas stations) or if invalid coordinates are provided.
* `500 Internal Server Error`: If the external mapping API is completely unresponsive.

---

## 🧪 Testing

The algorithm is fully covered by automated tests to mathematically prove the Greedy logic correctly handles edge cases (e.g., skipping an expensive station for a cheaper one vs. filling up when only expensive stations are ahead).

```bash
docker-compose -f docker-compose.dev.yml exec web pytest routing/tests.py
```
