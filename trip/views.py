from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripInputSerializer
from .route_service import build_route_segments
from .hos_logic import calculate_trip_schedule, calculate_total_trip_miles


class TripView(APIView):

    def post(self, request):
        serializer = TripInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        current_location = data['current_location']
        pickup_location = data['pickup_location']
        dropoff_location = data['dropoff_location']
        current_cycle_used = data['current_cycle_used']

        try:
            # Step 1: Get route from OpenRouteService
            segments, geocoded, full_geometry = build_route_segments(
                current_location, pickup_location, dropoff_location
            )

            # Step 2: Calculate HOS schedule
            days = calculate_trip_schedule(
                current_location=geocoded['current']['label'],
                pickup_location=geocoded['pickup']['label'],
                dropoff_location=geocoded['dropoff']['label'],
                current_cycle_used=current_cycle_used,
                route_segments=segments,
            )

            total_miles = calculate_total_trip_miles(segments)
            total_days = len(days)

            return Response({
                'success': True,
                'trip_summary': {
                    'total_miles': round(total_miles, 1),
                    'total_days': total_days,
                    'current_location': geocoded['current']['label'],
                    'pickup_location': geocoded['pickup']['label'],
                    'dropoff_location': geocoded['dropoff']['label'],
                },
                'geocoded': {
                    'current': geocoded['current'],
                    'pickup': geocoded['pickup'],
                    'dropoff': geocoded['dropoff'],
                },
                'route_geometry': full_geometry,
                'segments': [
                    {
                        'from': s['from'],
                        'to': s['to'],
                        'distance_miles': s['distance_miles'],
                        'duration_hours': s['duration_hours'],
                    }
                    for s in segments
                ],
                'days': days,
            })

        except ValueError as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'success': False, 'error': f'Route service error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
