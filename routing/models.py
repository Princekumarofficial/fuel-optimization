from django.db import models

class FuelStation(models.Model):
    opis_id = models.IntegerField(unique=True, help_text="OPIS Truckstop ID")
    name = models.CharField(max_length=255, help_text="Truckstop Name")
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.FloatField(help_text="Retail Price per gallon")
    
    # Geocoded Data
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        # Index on lat/lon to speed up standard geospatial bounding box queries
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['state']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state} (${self.retail_price})"
