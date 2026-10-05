from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import calculate_optimized_trip
import logging

logger = logging.getLogger(__name__)

class RouteOptimizationView(APIView):
    def post(self, request):
        """
        Expects JSON payload:
        {
            "start_lon": -74.0060,
            "start_lat": 40.7128,
            "end_lon": -118.2437,
            "end_lat": 34.0522
        }
        """
        try:
            start_lon = float(request.data.get('start_lon'))
            start_lat = float(request.data.get('start_lat'))
            end_lon = float(request.data.get('end_lon'))
            end_lat = float(request.data.get('end_lat'))
        except (TypeError, ValueError):
            return Response(
                {"error": "Please provide valid float coordinates for start and end locations."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            result = calculate_optimized_trip(start_lon, start_lat, end_lon, end_lat)
            return Response(result, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Route calculation failed: {e}", exc_info=True)
            return Response(
                {"error": "An internal server error occurred while calculating the route."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
