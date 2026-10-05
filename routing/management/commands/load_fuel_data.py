import csv
import os
from django.core.management.base import BaseCommand
from routing.models import FuelStation

class Command(BaseCommand):
    help = 'Loads fuel station data from the geocoded CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the geocoded CSV file (e.g., fuel_geocoded.csv)')

    def handle(self, *args, **kwargs):
        csv_path = kwargs['csv_file']
        
        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        self.stdout.write("Deleting existing FuelStation data...")
        FuelStation.objects.all().delete()
        
        stations = []
        seen_ids = set()
        
        self.stdout.write("Reading CSV...")
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Parse numerical values
                    opis_id = int(row.get('OPIS Truckstop ID', 0))
                    if not opis_id or opis_id in seen_ids:
                        continue
                        
                    seen_ids.add(opis_id)
                    
                    rack_id_str = row.get('Rack ID', '')
                    rack_id = int(rack_id_str) if rack_id_str.isdigit() else None
                    
                    price_str = row.get('Retail Price', '0')
                    price = float(price_str) if price_str else 0.0
                    
                    lat_str = row.get('Latitude', '')
                    lon_str = row.get('Longitude', '')
                    lat = float(lat_str) if lat_str else None
                    lon = float(lon_str) if lon_str else None
                    
                    station = FuelStation(
                        opis_id=opis_id,
                        name=row.get('Truckstop Name', '').strip()[:255],
                        address=row.get('Address', '').strip()[:255],
                        city=row.get('City', '').strip()[:100],
                        state=row.get('State', '').strip()[:2],
                        rack_id=rack_id,
                        retail_price=price,
                        latitude=lat,
                        longitude=lon
                    )
                    stations.append(station)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not parse row {row.get('OPIS Truckstop ID')}: {e}"))

        self.stdout.write(f"Bulk creating {len(stations)} stations... this might take a moment.")
        
        # Batch bulk create
        batch_size = 1000
        for i in range(0, len(stations), batch_size):
            batch = stations[i:i + batch_size]
            FuelStation.objects.bulk_create(batch)
            
        self.stdout.write(self.style.SUCCESS(f"Successfully loaded {len(stations)} fuel stations into the database."))
