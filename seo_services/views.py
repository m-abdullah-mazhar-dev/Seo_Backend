from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from seo_services.dataforseo import fetch_keyword_metrics, fetch_keyword_suggestions
from seo_services.scrape import get_paa_questions
from seo_services.upload_blog_to_wp import *
from.serializers import *
from rest_framework.response import Response
from rest_framework import status
import base64 , requests
from datetime import time, timedelta
from django.utils import timezone
from SEO_Automation import settings
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import re
from .utils import call_dataforseo_keyword_suggestions, create_stripe_product_and_price, extract_keyword_suggestions, find_best_keyword_alternative
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import api_view, permission_classes


import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)

class PackageCreateAPIView(APIView):
    def post(self, request):
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            price_usd = Decimal(request.data.get("price_usd", 0))
            package = serializer.save(price=price_usd)

            # You must pass amount in cents, for example: $49.99 = 4999
            try:
                amount_cents = int(request.data.get("price_usd", 0)) * 100
                if amount_cents <= 0:
                    return Response({"error": "Valid price_usd required"}, status=400)

                product_id, price_id = create_stripe_product_and_price(
                    package, amount_cents=amount_cents
                )

                package.stripe_product_id = product_id
                package.stripe_price_id = price_id
                package.save()

                return Response(PackageSerializer(package).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                package.delete()  # Cleanup on error
                return Response({"error": str(e)}, status=500)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, pk=None):
        if pk:
            package = get_object_or_404(Package, pk=pk)
            serializer = PackageSerializer(package)
            return Response(serializer.data, status=status.HTTP_200_OK)
        packages = Package.objects.all()
        serializer = PackageSerializer(packages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        package = get_object_or_404(Package, pk=pk)
        serializer = PackageSerializer(package, data=request.data, partial=True)

        if serializer.is_valid():
            price_usd = request.data.get("price")
            if price_usd:
                amount_cents = int(Decimal(price_usd) * 100)

                # Create new Stripe Price
                try:
                    _, new_price_id = create_stripe_product_and_price(
                        package, amount_cents=amount_cents
                    )
                    package.stripe_price_id = new_price_id
                except Exception as e:
                    return Response({"error": f"Stripe error: {str(e)}"}, status=500)

            serializer.save(price=price_usd)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        package = get_object_or_404(Package, pk=pk)
        try:
            # Optional: delete from Stripe too
            if package.stripe_product_id:
                stripe.Product.modify(
                    package.stripe_product_id,
                    active=False  # safer than deleting (keeps history)
                )
            package.delete()
            return Response({"message": "Package deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OnBoardingFormAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        print(request.user, "********** USER IN VIEW **********")
        print(request.auth, "********** AUTH **********")

        serializer = OnBoardingFormSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Onboarding form submitted successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            {
                "errors": serializer.errors,
                "message": "Invalid data provided."
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    
    def get(self, request, pk=None):
        if pk:
            try:
                onboarding_form = OnboardingForm.objects.get(pk=pk, user=request.user)
                serializer = OnBoardingFormSerializer(onboarding_form)
                return Response({"message": "Onboarding form retrieved successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
            except OnboardingForm.DoesNotExist:
                return Response({"message": "Onboarding form not found."}, status=status.HTTP_404_NOT_FOUND)

        onboarding_forms = OnboardingForm.objects.filter(user=request.user)
        serializer = OnBoardingFormSerializer(onboarding_forms, many=True)
        return Response({"message": "Onboarding forms retrieved successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
    
    
    def put(self, request, pk=None):
        if not pk:
            return Response({"message": "Onboarding form ID is required for update."}, status=status.HTTP_400_BAD_REQUEST)

        onboarding_form = get_object_or_404(OnboardingForm, pk=pk, user=request.user)

        serializer = OnBoardingFormSerializer(
            onboarding_form,
            data=request.data,
            partial=True,  # Allow partial updates
            context={'request': request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Onboarding form updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK
            )

        return Response(
            {"errors": serializer.errors, "message": "Invalid data provided."},
            status=status.HTTP_400_BAD_REQUEST
        )
from concurrent.futures import ThreadPoolExecutor
from geopy.exc import GeocoderTimedOut
from geopy import OpenCage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from geopy.distance import geodesic

# class NearbyAreasAPIView(APIView):
#     def post(self, request):
#         # Extract area_name and radius from the request data
#         area_name = request.data.get("area_name")
#         radius = request.data.get("radius", 10)  # Default to 10 miles if not provided

#         if not area_name:
#             return Response({"message": "Area name is required"}, status=status.HTTP_400_BAD_REQUEST)

#         # Step 1: Get coordinates of the area_name using Geopy (using threads for parallel geocoding)
#         center_lat, center_lng = self.get_coordinates(area_name)
#         if center_lat is None or center_lng is None:
#             return Response({"message": "Area not found"}, status=status.HTTP_404_NOT_FOUND)

#         # Step 2: Get nearby locations using Overpass API
#         nearby_areas = self.get_nearby_areas(center_lat, center_lng, radius)

#         # Step 3: Filter areas within the radius
#         nearby_areas = self.filter_areas_within_radius(nearby_areas, center_lat, center_lng, radius)

#         # Step 4: Return the result in the required format
#         result = {
#             "center": {"lat": center_lat, "lng": center_lng},
#             "areas": nearby_areas[:20]  # Limit to 20 areas
#         }
#         return Response(result, status=status.HTTP_200_OK)

#     def get_coordinates(self, area_name):
#         """Fetch the coordinates for a given area name using OpenCage API, with retry on timeout."""
#         key = "dc5c08222b53419da5ff59e9fbdeb91d"
#         geolocator = OpenCage(api_key=key)

#         try:
#             location = geolocator.geocode(area_name, timeout=10)  # Increased timeout
#             if location:
#                 return location.latitude, location.longitude
#             else:
#                 return None, None
#         except GeocoderTimedOut:
#             return None, None
#         except Exception as e:
#             print(f"Error occurred: {e}")
#             return None, None

#     def get_nearby_areas(self, center_lat, center_lng, radius):
#         """Fetch nearby areas using Overpass API and filter them by radius."""
#         overpass_url = "http://overpass-api.de/api/interpreter"
        
#         overpass_query = f"""
#         [out:json];
#         (
#             node["amenity"](around:{radius * 1609.34},{center_lat},{center_lng});
#             node["place"](around:{radius * 1609.34},{center_lat},{center_lng});
#             node["building"](around:{radius * 1609.34},{center_lat},{center_lng});
#             node["shop"](around:{radius * 1609.34},{center_lat},{center_lng});
#             node["highway"](around:{radius * 1609.34},{center_lat},{center_lng});
#             way["amenity"](around:{radius * 1609.34},{center_lat},{center_lng});
#             way["place"](around:{radius * 1609.34},{center_lat},{center_lng});
#             way["building"](around:{radius * 1609.34},{center_lat},{center_lng});
#             way["shop"](around:{radius * 1609.34},{center_lat},{center_lng});
#             way["highway"](around:{radius * 1609.34},{center_lat},{center_lng});
#             relation["amenity"](around:{radius * 1609.34},{center_lat},{center_lng});
#             relation["place"](around:{radius * 1609.34},{center_lat},{center_lng});
#             relation["building"](around:{radius * 1609.34},{center_lat},{center_lng});
#             relation["shop"](around:{radius * 1609.34},{center_lat},{center_lng});
#             relation["highway"](around:{radius * 1609.34},{center_lat},{center_lng});
#         );
#         out body 20;
#         """
#         response = requests.get(overpass_url, params={'data': overpass_query})
#         data = response.json()

#         # List of nearby areas
#         nearby_areas = []
#         for element in data['elements']:
#             if 'tags' in element and 'name' in element['tags']:
#                 name = element['tags']['name']
#                 lat = element['lat'] if 'lat' in element else None
#                 lng = element['lon'] if 'lon' in element else None

#                 if lat and lng:
#                     nearby_areas.append({"name": name, "lat": lat, "lng": lng})

#         return nearby_areas

#     def filter_areas_within_radius(self, areas, center_lat, center_lng, radius):
#         """Filter the areas that are within the radius using multiple threads."""
#         with ThreadPoolExecutor() as executor:
#             results = list(executor.map(lambda area: self.calculate_distance(area, center_lat, center_lng, radius), areas))

#         # Filter out areas that are beyond the radius
#         return [area for area, is_within in zip(areas, results) if is_within]

#     def calculate_distance(self, area, center_lat, center_lng, radius):
#         """Calculate the distance and check if the area is within the radius."""
#         distance = geodesic((center_lat, center_lng), (area['lat'], area['lng'])).miles
#         return distance <= radius

# update

import googlemaps
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from geopy.distance import geodesic

class NearbyAreasAPIView(APIView):
    def post(self, request):
        # Extract area_name, location_url and radius from the request data
        area_name = request.data.get("area_name")
        location_url = request.data.get("location_url")
        radius = request.data.get("radius", 10)  # Default to 10 miles if not provided

        if not area_name and not location_url:
            return Response({"message": "Either area_name or location_url is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Get coordinates using either area_name or location_url
        if location_url:
            center_lat, center_lng = self.get_coordinates_from_url(location_url)
        else:
            center_lat, center_lng = self.get_coordinates(area_name)
            
        if center_lat is None or center_lng is None:
            return Response({"message": "Location not found"}, status=status.HTTP_404_NOT_FOUND)

        # Step 2: Get nearby areas using Google Places API
        nearby_areas = self.get_nearby_areas(center_lat, center_lng, radius)

        # Step 3: Filter areas within the exact radius and remove duplicates
        filtered_areas = self.filter_areas_within_radius(nearby_areas, center_lat, center_lng, radius)
        
        # Remove duplicates by name and ensure minimum 20 results
        unique_areas = self.remove_duplicates(filtered_areas)
        
        # If we have less than 20 results, try to get more using different methods
        if len(unique_areas) < 20:
            additional_areas = self.get_additional_areas(center_lat, center_lng, radius, unique_areas)
            unique_areas.extend(additional_areas)
            unique_areas = self.remove_duplicates(unique_areas)

        # Step 4: Sort areas by distance (closest first) and add distance info
        sorted_areas = self.sort_areas_by_distance(unique_areas, center_lat, center_lng)

        # Step 5: Return the result in the required format
        result = {
            "center": {"lat": center_lat, "lng": center_lng},
            "areas": sorted_areas[:20]  # Ensure exactly 20 areas, sorted by distance
        }
        return Response(result, status=status.HTTP_200_OK)

    def get_coordinates(self, area_name):
        """Fetch the coordinates for a given area name using Google Geocoding API."""
        try:
            gmaps = googlemaps.Client(key="AIzaSyDNdts5OXZbt-RWwxeFcz4pi6E2EqPSl7s")
            geocode_result = gmaps.geocode(area_name)
            
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                return location['lat'], location['lng']
            else:
                return None, None
        except Exception as e:
            print(f"Error occurred in geocoding: {e}")
            return None, None

    def get_coordinates_from_url(self, location_url):
        """Extract coordinates from a location URL using Google Geocoding API."""
        try:
            gmaps = googlemaps.Client(key="AIzaSyDNdts5OXZbt-RWwxeFcz4pi6E2EqPSl7s")
            
            # First, try to resolve short URLs to get the full URL
            try:
                import requests
                response = requests.get(location_url, allow_redirects=True, timeout=10)
                full_url = response.url
                print(f"Resolved URL: {full_url}")
            except Exception as e:
                print(f"Error resolving URL: {e}")
                full_url = location_url
            
            # Try to extract coordinates from the URL pattern
            coordinates = self.extract_coordinates_from_url(full_url)
            if coordinates:
                return coordinates
            
            # Try to geocode the URL directly
            geocode_result = gmaps.geocode(location_url)
            
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                return location['lat'], location['lng']
            else:
                # Try with the resolved URL
                geocode_result = gmaps.geocode(full_url)
                if geocode_result:
                    location = geocode_result[0]['geometry']['location']
                    return location['lat'], location['lng']
                else:
                    return None, None
        except Exception as e:
            print(f"Error occurred in URL geocoding: {e}")
            return None, None

    def extract_coordinates_from_url(self, url):
        """Extract coordinates from Google Maps URL patterns."""
        try:
            import re
            
            # Pattern for Google Maps URLs with coordinates (@lat,lng)
            coord_pattern = r'@(-?\d+\.\d+),(-?\d+\.\d+)'
            match = re.search(coord_pattern, url)
            
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))
                return lat, lng
            
            # Pattern for Google Maps search URLs with coordinates (31.438128,+73.131748)
            search_coord_pattern = r'search/(\d+\.\d+),\+?(\d+\.\d+)'
            search_match = re.search(search_coord_pattern, url)
            
            if search_match:
                lat = float(search_match.group(1))
                lng = float(search_match.group(2))
                return lat, lng
            
            # Pattern for Google Maps URLs with place IDs or addresses
            # Try to extract address from URL
            if 'maps.google.com' in url or 'maps.app.goo.gl' in url:
                # Try to extract place name from URL
                place_pattern = r'place/([^/]+)'
                place_match = re.search(place_pattern, url)
                if place_match:
                    place_name = place_match.group(1).replace('+', ' ')
                    # Try to geocode the place name
                    gmaps = googlemaps.Client(key="AIzaSyDNdts5OXZbt-RWwxeFcz4pi6E2EqPSl7s")
                    geocode_result = gmaps.geocode(place_name)
                    if geocode_result:
                        location = geocode_result[0]['geometry']['location']
                        return location['lat'], location['lng']
            
            return None
        except Exception as e:
            print(f"Error extracting coordinates from URL: {e}")
            return None

    def get_nearby_areas(self, center_lat, center_lng, radius):
        """Fetch nearby areas using Google Places API with specific area-focused searches."""
        try:
            gmaps = googlemaps.Client(key="AIzaSyDNdts5OXZbt-RWwxeFcz4pi6E2EqPSl7s")
            
            # Convert miles to meters (Google Places API uses meters)
            radius_meters = radius * 1609.34
            
            nearby_areas = []
            
            # Search queries specifically for areas, towns, neighborhoods
            area_queries = [
                "town", "neighborhood", "colony", "sector", "block", 
                "area", "locality", "village", "township", "settlement",
                "community", "district", "quarter", "ward", "zone"
            ]
            
            for query in area_queries:
                try:
                    # Search for areas using text search
                    places_result = gmaps.places(
                        query=query,
                        location=(center_lat, center_lng),
                        radius=radius_meters,
                        type='locality'  # Focus on locality types
                    )
                    
                    for place in places_result.get('results', []):
                        area_data = self.extract_area_data(place, center_lat, center_lng)
                        if area_data and area_data not in nearby_areas:
                            nearby_areas.append(area_data)
                            
                except Exception as e:
                    print(f"Error searching for {query}: {e}")
                    continue

            # Additional search for specific place types that represent areas
            area_types = ['locality', 'sublocality', 'neighborhood', 'political']
            
            for place_type in area_types:
                try:
                    places_result = gmaps.places_nearby(
                        location=(center_lat, center_lng),
                        radius=radius_meters,
                        type=place_type
                    )
                    
                    for place in places_result.get('results', []):
                        area_data = self.extract_area_data(place, center_lat, center_lng)
                        if area_data and area_data not in nearby_areas:
                            nearby_areas.append(area_data)
                            
                except Exception as e:
                    print(f"Error searching type {place_type}: {e}")
                    continue

            return nearby_areas
            
        except Exception as e:
            print(f"Error occurred in Google Places API: {e}")
            return []

    def extract_area_data(self, place, center_lat, center_lng):
        """Extract area data from Google Places result."""
        try:
            name = place.get('name', '')
            types = place.get('types', [])
            
            # Filter out non-area places
            if not self.is_valid_area(name, types):
                return None
            
            lat = place['geometry']['location']['lat']
            lng = place['geometry']['location']['lng']
            
            return {
                "name": name,
                "lat": lat,
                "lng": lng
            }
        except Exception as e:
            print(f"Error extracting area data: {e}")
            return None

    def is_valid_area(self, name, types):
        """Check if this is a valid area name (not a specific POI)."""
        if not name or name.lower() == 'unnamed':
            return False
        
        # Exclude specific point of interest types
        excluded_types = [
            'establishment', 'point_of_interest', 'food', 'restaurant', 
            'mosque', 'church', 'temple', 'hospital', 'school', 'university',
            'store', 'shop', 'mall', 'bank', 'atm', 'gas_station', 'parking'
        ]
        
        # If it has any excluded types, it's probably not an area
        if any(excluded in types for excluded in excluded_types):
            return False
        
        # Valid area indicators
        area_indicators = [
            'town', 'village', 'city', 'borough', 'district', 
            'neighborhood', 'suburb', 'locality', 'municipality',
            'colony', 'sector', 'block', 'area', 'township'
        ]
        
        name_lower = name.lower()
        
        # Check if name contains area indicators or is a simple name
        return (any(indicator in name_lower for indicator in area_indicators) or
                'locality' in types or 'sublocality' in types or 
                'neighborhood' in types or 'political' in types)

    def filter_areas_within_radius(self, areas, center_lat, center_lng, radius):
        """Filter areas to ensure they are within the exact radius."""
        filtered_areas = []
        
        for area in areas:
            try:
                distance = geodesic((center_lat, center_lng), (area['lat'], area['lng'])).miles
                if distance <= radius:
                    filtered_areas.append(area)
            except Exception as e:
                print(f"Error calculating distance: {e}")
                continue
                
        return filtered_areas

    def remove_duplicates(self, areas):
        """Remove duplicate areas by name."""
        seen_names = set()
        unique_areas = []
        
        for area in areas:
            if area['name'] not in seen_names:
                seen_names.add(area['name'])
                unique_areas.append(area)
                
        return unique_areas

    def get_additional_areas(self, center_lat, center_lng, radius, existing_areas):
        """Get additional areas if we don't have enough results."""
        try:
            gmaps = googlemaps.Client(key="AIzaSyDNdts5OXZbt-RWwxeFcz4pi6E2EqPSl7s")
            radius_meters = radius * 1609.34
            
            existing_names = {area['name'] for area in existing_areas}
            additional_areas = []
            
            # Try broader searches
            broader_searches = [
                "residential area", "housing society", "town", "village"
            ]
            
            for search_term in broader_searches:
                try:
                    places_result = gmaps.places(
                        query=search_term,
                        location=(center_lat, center_lng),
                        radius=radius_meters
                    )
                    
                    for place in places_result.get('results', []):
                        area_data = self.extract_area_data(place, center_lat, center_lng)
                        if (area_data and area_data['name'] not in existing_names and
                            area_data not in additional_areas):
                            additional_areas.append(area_data)
                            
                except Exception as e:
                    print(f"Error in broader search {search_term}: {e}")
                    continue
            
            return additional_areas
            
        except Exception as e:
            print(f"Error getting additional areas: {e}")
            return []

    def sort_areas_by_distance(self, areas, center_lat, center_lng):
        """Sort areas by distance from center point (closest first) and add distance info."""
        try:
            areas_with_distance = []
            
            for area in areas:
                try:
                    # Calculate distance in miles
                    distance = geodesic((center_lat, center_lng), (area['lat'], area['lng'])).miles
                    
                    # Add distance to area data
                    area_with_distance = {
                        'name': area['name'],
                        'lat': area['lat'],
                        'lng': area['lng'],
                        'distance': round(distance, 2)  # Round to 2 decimal places
                    }
                    areas_with_distance.append(area_with_distance)
                    
                except Exception as e:
                    print(f"Error calculating distance for {area.get('name', 'unknown')}: {e}")
                    continue
            
            # Sort by distance (closest first)
            sorted_areas = sorted(areas_with_distance, key=lambda x: x['distance'])
            
            return sorted_areas
            
        except Exception as e:
            print(f"Error sorting areas by distance: {e}")
            return areas  # Return original areas if sorting fails









class CompanyDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        onboarding_form = OnboardingForm.objects.filter(user=request.user).first()
        if not onboarding_form:
            return Response({"message": "No company details found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CompanyDetailsSerializer(onboarding_form)
        return Response(serializer.data, status=status.HTTP_200_OK)




class CompanyDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        onboarding_form = OnboardingForm.objects.filter(user=request.user).first()
        if not onboarding_form:
            return Response({"message": "No company details found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CompanyDetailsSerializer(onboarding_form)
        return Response(serializer.data, status=status.HTTP_200_OK)


def generate_wordpress_token(username, application_password):
    credentials = f"{username}:{application_password}"
    token = base64.b64encode(credentials.encode()).decode()
    return token


# class ConnectWordPressAPI(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         site_url = request.data.get('site_url')
#         username = request.data.get('username', '').strip()
#         app_password = request.data.get('app_password', '').strip()

#         if not all([site_url, username, app_password]):
#             return Response({"error": "Missing required fields."}, status=400)

#         # 🔹 Generate and store the access token (base64 encoded)
#         access_token = generate_wordpress_token(username, app_password)

#         wp_conn, created = WordPressConnection.objects.update_or_create(
#             user=request.user,
#             defaults={
#                 'site_url': site_url,
#                 'access_token': access_token  # ✅ Now we only need the token
#             }
#         )

#         return Response({"message": "WordPress connected successfully."})


class ConnectWordPressAPI(APIView):
    """
    Try to connect to WordPress.
    Only create DB entry if verified successfully.
    If already exists for the user → return error.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        site_url = request.data.get('site_url', '').strip()
        username = request.data.get('username', '').strip()
        app_password = request.data.get('app_password', '').strip()

        if not all([site_url, username, app_password]):
            return Response({"error": "Missing required fields."}, status=400)
        
        if not hasattr(request.user, "usersubscription") or request.user.usersubscription.status != "active":
            return Response(
                {"error": "User Dosen't have subscription"},
                status=400
            )

        # 🔹 Check if connection already exists for this user
        if hasattr(request.user, "wordpress_connection"):
            return Response(
                {"error": "WordPress connection already exists for this user."},
                status=400
            )

        # 🔹 Generate token
        access_token = generate_wordpress_token(username, app_password)

        # 🔹 Verify first before saving
        url = f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me"
        headers = {'Authorization': f'Basic {access_token.strip()}'}

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # ✅ Save only if valid (create new)
                wp_conn = WordPressConnection.objects.create(
                    user=request.user,
                    site_url=site_url,
                    access_token=access_token,
                )


                # ✅ Create Service Page (directly using site_url as page_url)
                service_page = ServicePage.objects.create(
                    user=request.user,
                    wordpress_connection=wp_conn,
                    page_url=site_url,   # <-- use site_url directly
                    blog_required=True   # by default blog is required when connecting
                )

                # ✅ Get interval from user's package
                onboarding_form = OnboardingForm.objects.filter(user=request.user).first()
                if not onboarding_form or not onboarding_form.package:
                    return Response({"error": "User package not found."}, status=400)

                interval_days = onboarding_form.package.interval
                next_run = timezone.now()
                # next_run = timezone.now() + timedelta(days=interval_days)

                # ✅ Create SEO Optimization Task
                SEOTask.objects.create(
                    user=request.user,
                    service_page=service_page,
                    task_type="seo_optimization",
                    next_run=next_run
                )

                # ✅ Create Blog Writing Task
                SEOTask.objects.create(
                    user=request.user,
                    service_page=service_page,
                    task_type="blog_writing",
                    next_run=next_run
                )

                # ✅ Create Keyword Optimization Task
                SEOTask.objects.create(
                    user=request.user,
                    service_page=service_page,
                    task_type="keyword_optimization",
                    next_run=next_run
                )

                return Response({
                    "message": "WordPress connected & Service Page + Tasks created successfully.",
                    "created": True
                }, status=200)

            return Response({
                "error": "Invalid WordPress credentials.",
                "status_code": response.status_code,
            }, status=400)

        except RequestException as e:
            return Response({
                "error": "Connection failed.",
                "details": str(e)
            }, status=500)

class ConnectWordPressAPIJob(APIView):
    """
    Try to connect to WordPress.
    Only create DB entry if verified successfully.
    If already exists for the user → return error.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        site_url = request.data.get('site_url', '').strip()
        username = request.data.get('username', '').strip()
        app_password = request.data.get('app_password', '').strip()

        if not all([site_url, username, app_password]):
            return Response({"error": "Missing required fields."}, status=400)
        
        if not hasattr(request.user, "usersubscription") or request.user.usersubscription.status != "active":
            return Response(
                {"error": "User Dosen't have subscription"},
                status=400
            )

        # 🔹 Check if connection already exists for this user
        if hasattr(request.user, "wordpress_connection"):
            return Response(
                {"error": "WordPress connection already exists for this user."},
                status=400
            )

        # 🔹 Generate token
        access_token = generate_wordpress_token(username, app_password)

        # 🔹 Verify first before saving
        url = f"{site_url.rstrip('/')}/wp-json/wp/v2/users/me"
        headers = {'Authorization': f'Basic {access_token.strip()}'}

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # ✅ Save only if valid (create new)
                wp_conn = WordPressConnection.objects.create(
                    user=request.user,
                    site_url=site_url,
                    access_token=access_token,
                )


                

                return Response({
                    "message": "WordPress connected For job",
                    "created": True
                }, status=200)

            return Response({
                "error": "Invalid WordPress credentials.",
                "status_code": response.status_code,
            }, status=400)

        except RequestException as e:
            return Response({
                "error": "Connection failed.",
                "details": str(e)
            }, status=500)


class VerifyWordPressConnectionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            wp_conn = request.user.wordpress_connection
            print(type(wp_conn))
        except WordPressConnection.DoesNotExist:
            return Response({"error": "WordPress connection not found."}, status=404)

        url = f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/users/me"

        try:
            # 🔹 Prepare the Authorization Header
            headers = {
                'Authorization': f'Basic {wp_conn.access_token.strip()}'
            }

            print("URL: ", url)
            print("Access Token: ", wp_conn.access_token.strip())

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return Response({"message": "Connection is valid."})
            else:
                return Response({
                    "error": "Invalid connection.",
                    "status_code": response.status_code,
                    "response": response.text
                }, status=response.status_code)

        except RequestException as e:
            return Response({"error": "Connection failed.", "details": str(e)}, status=500)


class SubmitServicePageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        page_url = request.data.get("page_url")
        blog_required = request.data.get("blog_required", False)
        gmbp_required = request.data.get("gmbp_required", False)

        if not page_url:
            return Response({"error": "Page URL is required."}, status=400)

        # Check if user has connected WordPress
        try:
            wp_conn = user.wordpress_connection
        except WordPressConnection.DoesNotExist:
            return Response({"error": "User has not connected WordPress."}, status=400)

        # Create the Service Page
        service_page = ServicePage.objects.create(
            user=user,
            wordpress_connection=wp_conn,
            page_url=page_url,
            blog_required=blog_required
        )

        # Get interval from user's package
        onboarding_form = OnboardingForm.objects.filter(user=user).first()
        if not onboarding_form or not onboarding_form.package:
            return Response({"error": "User package not found."}, status=400)

        interval_days = onboarding_form.package.interval
        next_run = timezone.now()
        print(next_run)
        # next_run = timezone.now() + timedelta(days=interval_days)

        # Create SEO Optimization Task
        SEOTask.objects.create(
            user=user,
            service_page=service_page,
            task_type="seo_optimization",
            next_run=next_run
        )

        # Create Blog Writing Task (if blog_required)
        if blog_required:
            SEOTask.objects.create(
                user=user,
                service_page=service_page,
                task_type="blog_writing",
                next_run=next_run
            )
        
        # ✅ Add Keyword Optimization Task
        SEOTask.objects.create(
            user=user,
            service_page=service_page,
            task_type="keyword_optimization",
            next_run=next_run
        )
        if gmbp_required:
            SEOTask.objects.create(
                user=user,
                service_page=service_page,
                task_type="gmb_post",
                next_run=next_run
            )


        return Response({"message": "Service Page & Tasks created successfully."})



# def run_blog_writing(task):
#     logger = logging.getLogger(__name__)
#     try:
#         service = task.service_page
#         user = task.user

#         onboarding = OnboardingForm.objects.filter(user=user).first()
#         if not onboarding:
#             logger.warning("⚠️ No onboarding form found.")
#             task.status = "failed"
#             task.save()
#             return

#         # keywords = Keyword.objects.filter(
#         #     service__onboarding_form=onboarding
#         # ).values_list('keyword', flat=True)

#         keywords_objects = Keyword.objects.filter(
#             service__onboarding_form=onboarding
#         )

#         keywords = list(keywords_objects.values_list("keyword", flat=True))

#         logger.info(f"🔑 Keywords for blog generation: {list(keywords)}")

#         if not keywords_objects.exists():
#             task.status = "failed"
#             task.save()
#             return
        
#         # research_words = []
#         # for keyword in keywords_objects:
#         #     keyword_questions = keyword.questions.values_list("question", flat=True)
#         #     research_words.extend(keyword_questions)

#         # research_words = list(set(research_words))  # Remove duplicates
#         # logger.info(f"🧠 Research words: {research_words[:25]}... (total: {len(research_words)})")

#         ai_payload = {
#             "keywords": list(keywords),
#             # "research_words": research_words,
#             "type": "blog"
#         }
        

#         response = requests.post(
#             # f"{settings.AI_API_DOMAIN}/generate_blog_and_image",
#             f"{settings.AI_API_DOMAIN}/generate_content",
#             json=ai_payload,
#             timeout=60
#         )

#         if response.status_code != 200:
#             logger.error(f"❌ AI response error: {response.text}")
#             task.status = "failed"
#             task.ai_request_payload = ai_payload
#             task.ai_response_payload = {"error": response.text}
#             task.save()
#             return
        
#         data = response.json()

#         blog_html = data.get("content", "").strip()

        

#         image_url_raw = data.get("imageUrl", "")
#         image_url = re.sub(r"win\s+dows", "windows", image_url_raw)

#         # # Remove ```html markdown wrapper
#         # if blog_html.startswith("```html"):
#         #     blog_html = blog_html.replace("```html", "").replace("```", "").strip()
#         # Remove markdown fences
#         blog_html = re.sub(r"^```html\s*", "", blog_html)
#         blog_html = re.sub(r"```$", "", blog_html.strip())
#         if not blog_html:
#             logger.warning("⚠️ Blog content is empty after cleaning.")


#         # Extract <title>
#         soup = BeautifulSoup(blog_html, "html.parser")
#         # title = soup.title.string.strip() if soup.title else "Untitled Blog"
#         titles = soup.find_all("title")
#         title = titles[0].text.strip() if titles else "Untitled Blog"

#         logger.info("✅ Blog HTML received")
#         logger.info("📝 Blog HTML: %s", blog_html)
#         logger.info(f"🖼️ Image URL: {image_url}")
#         logger.info(f"📝 Blog Title: {title}")

     

#         blog = Blog.objects.create(
#             seo_task=task,
#             title=title,
#             content=blog_html
#         )

#         if image_url:
#             BlogImage.objects.create(blog=blog, image_url=image_url)

#         # 🔁 Monthly count logic
#         current_month = timezone.now().strftime('%Y-%m')
#         if task.month_year != current_month:
#             task.count_this_month = 0
#             task.month_year = current_month

#         task.count_this_month += 1

#         interval_days = onboarding.package.interval if onboarding.package else 7
#         task.ai_request_payload = ai_payload
#         task.ai_response_payload = data
#         task.last_run = timezone.now()
#         task.next_run = timezone.now() + timedelta(days=interval_days)
#         # task.next_run = timezone.now() + timezone.timedelta(minutes=3)
#         task.status = "completed"
#         task.save()


#         logger.info(f"✅ Task {task.id} completed successfully.")
#         try:
#             upload_blog_to_wordpress(blog, task.service_page.wordpress_connection)
        
#         except Exception as e:
#             logger.exception(f"❌ Wordpress blog upload failed: {str(e)}")


#         # 🔁 Auto-create next task if blog limit not reached
#         # 🔁 Auto-create next blog task if blog limit not reached
#         package = onboarding.package
#         if task.is_active and  task.count_this_month < package.blog_limit:
#             SEOTask.objects.create(
#                 user=user,
#                 service_page=task.service_page,
#                 task_type='blog_writing',
#                 next_run=task.last_run + timedelta(days=package.interval),
#                 # next_run = timezone.now() + timezone.timedelta(minutes=3),
#                 status='pending',
#                 count_this_month=task.count_this_month,
#                 month_year=current_month,
#                 is_active=True
#             )
#             logger.info(f"✅ New blog writing task created (this_month_count={task.count_this_month})")
#         else:
            
#             # ✅ Limit hit: Pause next task, will resume next month
#             SEOTask.objects.create(
#                 user=user,
#                 service_page=task.service_page,
#                 task_type='blog_writing',
#                 next_run=None,
#                 status='pending',
#                 count_this_month=0,  # new month will reset this
#                 month_year=current_month,
#                 is_active=True
#             )
#             logger.info(f"⏸️ Blog limit reached. Next task paused until new month.")

#     except Exception as e:
#         logger.exception(f"❌ Exception in run_blog_writing for task {task.id}: {str(e)}")
#         task.status = "failed"
#         task.ai_response_payload = {"error": str(e)}
#         task.save()




def run_blog_writing(task):
    logger = logging.getLogger(__name__)
    try:
        service_page = task.service_page
        user = task.user

        onboarding = OnboardingForm.objects.filter(user=user).first()
        if not onboarding:
            logger.warning("⚠️ No onboarding form found.")
            task.status = "failed"
            task.save()
            return

        services = onboarding.services.all()
        if not services.exists():
            logger.warning("⚠ No services found for Blog writing.")
            task.status = "failed"
            task.save()
            return

        # reset monthly count if it's a new month
        current_month = timezone.now().strftime('%Y-%m')
        if task.month_year != current_month:
            task.count_this_month = 0
            task.month_year = current_month

        all_payloads, all_responses = [], []

        # create a separate blog for each service
        for service in services:
            keywords = service.keywords.all()
            if not keywords.exists():
                logger.warning(f"⚠ No keywords found for service {service.service_name}")
                continue

            keyword_list = list(keywords.values_list("keyword", flat=True))
            topic = service.service_name

            logger.info(f"🔑 Keywords for Blog writing ({service.service_name}): {keyword_list}")

            ai_payload = {"keywords": keyword_list, "topic": topic}
            all_payloads.append(ai_payload)

            # try:
            response = requests.post(
                f"{settings.AI_API_DOMAIN}/generate_blog_and_image",
                json=ai_payload,
                timeout=60
            )
            if response.status_code != 200:
                logger.error(f"❌ AI API error for {service.service_name}: {response.text}")
                # continue
                raise Exception(f"AI API failed with status {response.status_code}: {response.text}")



            data = response.json()
            all_responses.append(data)

            blog_html = data.get("blog", "").strip()
            blog_html = re.sub(r"^```html\s*", "", blog_html)
            blog_html = re.sub(r"```$", "", blog_html.strip())
            if not blog_html:
                logger.warning(f"⚠ Empty blog content received for {service.service_name}")
                continue

            soup = BeautifulSoup(blog_html, "html.parser")
            titles = soup.find_all("title")
            title = data.get("refinedTopic") or (titles[0].text.strip() if titles else "Untitled Blog")

            logger.info(f"✅ Blog created for service {service.service_name}")
            logger.info(f"📝 Blog Title: {title}")
            logger.info(f"🖼️ Image URL: {data.get('imageUrl', '')}")

            blog = Blog.objects.create(seo_task=task, title=title, content=blog_html)

            if data.get("imageUrl"):
                BlogImage.objects.create(blog=blog, image_url=data["imageUrl"])

            try:
                upload_blog_to_wordpress(blog, service_page.wordpress_connection)
            except Exception as e:
                logger.exception(f"❌ Wordpress blog upload failed for {service.service_name}: {str(e)}")

            # ✅ increment per blog
            task.count_this_month += 1

            # except Exception as e:
            #     logger.error(f"❌ Error creating Blog for {service.service_name}: {str(e)}")
            #     continue

        # bookkeeping
        interval_days = onboarding.package.interval if onboarding.package else 7
        task.ai_request_payload = all_payloads
        task.ai_response_payload = all_responses
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=interval_days)
        task.status = "completed"
        task.failure_count = 0  # ← Reset on success
        task.last_failure_reason = None  # ← Clear failure reason
        task.save()

        package = onboarding.package
        if package and task.is_active and task.count_this_month < package.blog_limit:
            SEOTask.objects.create(
                user=user,
                service_page=service_page,
                task_type='blog_writing',
                next_run=task.last_run + timedelta(days=package.interval),
                status='pending',
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True
            )
            logger.info(f"✅ New blog writing task created (this_month_count={task.count_this_month})")
        else:
            SEOTask.objects.create(
                user=user,
                service_page=service_page,
                task_type='blog_writing',
                next_run=None,
                status='pending',
                count_this_month=0,  # will reset next month
                month_year=current_month,
                is_active=True
            )
            logger.info("⏸️ Blog limit reached. Next task paused until new month.")

    except Exception as e:
        logger.exception(f"❌ Exception in run_blog_writing for task {task.id}: {str(e)}")
        # task.status = "failed"
        # task.ai_response_payload = {"error": str(e)}
        # task.save()
        raise



# def run_seo_optimization(task):
#     logger = logging.getLogger(__name__)
#     try:
#         logger.info(f"🚀 Running SEO optimization task for Task ID {task.id}")
#         service_page = task.service_page
#         user = task.user

#         onboarding = OnboardingForm.objects.filter(user=user).first()
#         if not onboarding:
#             logger.warning("⚠️ No onboarding form found.")
#             task.status = "failed"
#             task.save()
#             return
        
#         #  Monthly check
#         current_month = timezone.now().strftime("%Y-%m")
#         package_limit = onboarding.package.seo_optimization_limit if onboarding.package else 5  # adjust default if needed

        
#         if task.month_year != current_month:
#             task.count_this_month = 0
#             task.month_year = current_month

#         # Check if limit reached
#         if task.count_this_month >= package_limit:
#             logger.warning("🚫 SEO task limit reached for this month.")
#             task.status = "skipped"
#             task.save()
#             return

#         # 🔑 Get all keywords related to services for this user
#         # keywords = Keyword.objects.filter(
#         #     service__onboarding_form=onboarding
#         # ).values_list("keyword", flat=True)
#         # keyword_qs = Keyword.objects.filter(
#         #     service__onboarding_form=onboarding
#         # )
#         # keywords = list(keyword_qs.values_list("keyword", flat=True))


#         # if not keywords:
#         #     logger.warning("⚠️ No keywords found for SEO optimization.")
#         #     task.status = "failed"
#         #     task.save()
#         #     return

#         # questions = KeywordQuestion.objects.filter(keyword__in=keyword_qs)
#         # research_words = list(questions.values_list("question", flat=True))

#         # logger.info(f"🔑 Keywords: {keywords}")
#         # logger.info(f"📚 Research Words: {research_words[:10]}...")

#          # 🌍 Get area names from ServiceAreas
#         # service_areas = onboarding.service_areas.all()
#         # area_names = list(service_areas.values_list("area_name", flat=True))
#         # area = ", ".join(area_names)
#         # logger.info(f"📍 Area(s): {area}")


#         # 🧠 AI Content Generation
#         # ai_payload = {
#         #     "keywords": keywords,
#         #     "research_words": research_words,
#         #     "area": area,
#         #     "type": "service_area"
#         # }

#         # # 🌐 Fetch current HTML content from service page URL
#         # try:
#         #     page_response = requests.get(service_page.page_url, timeout=20)
#         #     page_response.raise_for_status()
#         #     page_content = page_response.text
#         # except Exception as e:
#         #     logger.exception(f"❌ Failed to fetch page content: {str(e)}")
#         #     task.status = "failed"
#         #     task.ai_response_payload = {"error": str(e)}
#         #     task.save()
#         #     return

#         # # 📡 Send to optimization API
#         # api_payload = {
#         #     "keywords": list(keywords),
#         #     "content": page_content,
#         # }



#         # Get service areas
#         service_areas = onboarding.service_areas.all()
#         if not service_areas:
#             logger.warning("⚠️ No service areas found.")
#             task.status = "failed"
#             task.save()
#             return

#         # Get all services
#         services = Service.objects.filter(onboarding_form=onboarding)
#         if not services:
#             logger.warning("⚠️ No services found.")
#             task.status = "failed"
#             task.save()
#             return
        

#         # Process each service and area combination
#         for service in services:
#             # Get keywords for this specific service
#             keywords = list(service.keywords.values_list("keyword", flat=True))
            
#             if not keywords:
#                 logger.warning(f"⚠️ No keywords found for service: {service.service_name}")
#                 continue
            
#             for area in service_areas:
#                 logger.info(f"🔧 Processing service '{service.service_name}' for area '{area.area_name}'")
                
#                 # Check if we've reached the monthly limit
#                 if task.count_this_month >= package_limit:
#                     logger.warning("🚫 Monthly limit reached, stopping processing.")
#                     break
                
#                 # Check if this service-area page already exists
#                 existing_page_url = f"{service_page.page_url}/{service.service_name.lower().replace(' ', '-')}-in-{area.area_name.lower().replace(' ', '-')}"
#                 page_exists = ServicePage.objects.filter(
#                     user=user, 
#                     page_url=existing_page_url
#                 ).exists()
                
#                 # Determine which API to use based on whether page exists
#                 if page_exists:
#                     # Page exists, use optimization API
#                     try:
#                         page_response = requests.get(existing_page_url, timeout=20)
#                         page_response.raise_for_status()
#                         page_content = page_response.text
#                     except Exception as e:
#                         logger.exception(f"❌ Failed to fetch page content: {str(e)}")
#                         continue
                    
#                     api_url = f"{settings.AI_API_DOMAIN}/optimize_content"
#                     api_payload = {
#                         "content": page_content,
#                         "keywords": keywords,
#                         "area": area.area_name
#                     }
#                 else:
#                     # Page doesn't exist, use content generation API
#                     api_url = f"{settings.AI_API_DOMAIN}/generate_content"
#                     api_payload = {
#                         "keywords": keywords,
#                         "area": area.area_name,
#                         "type": "service_area"
#                     }
                
#                 # Call the appropriate API
#                 api_response = requests.post(
#                     api_url,
#                     json=api_payload,
#                     timeout=60
#                 )

#                 if api_response.status_code != 200:
#                     logger.error(f"❌ API response error: {api_response.text}")
#                     continue

#                 optimized_data = api_response.json()
#                 optimized_content = optimized_data.get("content") or optimized_data.get("optimizedContent")
                
#                 if not optimized_content:
#                     logger.warning("⚠️ No optimized content received.")
#                     continue
                
#                 # Upload to WordPress
#                 try:
#                     final_url = upload_service_page_to_wordpress(
#                         service_page, 
#                         optimized_content,
#                         service_name=service.service_name,
#                         area_name=area.area_name
#                     )
                    
#                     if final_url:
#                         # Update task information
#                         task.optimized_content = optimized_content
#                         task.ai_request_payload = api_payload
#                         task.ai_response_payload = optimized_data
#                         task.wp_page_url = final_url
#                         task.count_this_month += 1
#                         task.save()
                        
#                         logger.info(f"✅ Created/optimized page for {service.service_name} in {area.area_name}: {final_url}")
#                     else:
#                         logger.error(f"❌ Failed to upload page for {service.service_name} in {area.area_name}")
#                 except Exception as e:
#                     logger.exception(f"❌ WordPress upload failed: {str(e)}")
        
#         # Update task status
#         task.status = "completed"
#         task.last_run = timezone.now()
#         task.next_run = timezone.now() + timedelta(
#             days=onboarding.package.interval if onboarding.package else 7
#         )
#         task.month_year = current_month
#         task.save()

#         logger.info(f"✅ SEO Optimization Task {task.id} completed.")

#         # # 🧠 AI Content Generation
#         # api_payload = {
#         #     "keywords": keywords,
#         #     # "research_words": research_words,
#         #     "area": area,
#         #     "type": "service_area"
#         # }

#         # api_response = requests.post(
#         #     # f"{settings.AI_API_DOMAIN}/optimize_blog",
#         #     f"{settings.AI_API_DOMAIN}/generate_content",
#         #     json=api_payload,
#         #     timeout=60
#         # )

#         # if api_response.status_code != 200:
#         #     logger.error(f"❌ API response error: {api_response.text}")
#         #     task.status = "failed"
#         #     task.ai_request_payload = api_payload
#         #     task.ai_response_payload = {"error": api_response.text}
#         #     task.save()
#         #     return

#         # optimized_data = api_response.json()
#         # optimized_content = optimized_data.get("content")
#         # logger.info("📝 optimized content: %s", optimized_content)

#         # if not optimized_content:
#         #     logger.warning("⚠️ No optimized content received.")
#         #     task.status = "failed"
#         #     task.save()
#         #     return

#         # # ✅ Save optimized content
#         # task.optimized_content = optimized_content
#         # task.ai_request_payload = api_payload
#         # task.ai_response_payload = optimized_data
#         # task.status = "completed"
#         # task.last_run = timezone.now()
#         # task.next_run = timezone.now() + timedelta(days=onboarding.package.interval if onboarding.package else 7)
#         # task.month_year = current_month
#         # task.count_this_month +=1 
#         # task.save()

#         # logger.info(f"✅ SEO Optimization Task {task.id} completed and saved.")

#         # try:
#         #    final_url = upload_service_page_to_wordpress(task.service_page, task.optimized_content)
#         #    if final_url:
#         #         task.wp_page_url = final_url
#         #         task.save()
#         #         logger.info(f"✅ FInal url saved.{final_url}")

        
#         # except Exception as e:
#         #     logger.exception(f"❌ Wordpress blog upload failed: {str(e)}")

#         # create next task 
#         if task.count_this_month < package_limit:
#             SEOTask.objects.create(
#                 user=user,
#                 service_page=service_page,
#                 task_type='seo_optimization',
#                 next_run=task.next_run,
#                 status='pending',
#                 count_this_month=task.count_this_month,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("✅ Created next SEO task.")
#         else:
#             SEOTask.objects.create(
#                 user=user,
#                 service_page=service_page,
#                 task_type='seo_optimization',
#                 next_run=None,
#                 status='pending',
#                 count_this_month=0,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("⏸️ Limit reached, next SEO task paused for this month.")    

#     except Exception as e:
#         logger.exception(f"❌ Exception in SEO Optimization task: {str(e)}")
#         task.status = "failed"
#         task.ai_response_payload = {"error": str(e)}
#         task.save()


# def run_seo_optimization(task):
#     logger = logging.getLogger(__name__)
#     try:
#         logger.info(f"🚀 Running SEO optimization task for Task ID {task.id}")
#         user = task.user

#         onboarding = OnboardingForm.objects.filter(user=user).first()
#         if not onboarding:
#             logger.warning("⚠️ No onboarding form found.")
#             task.status = "failed"
#             task.save()
#             return
        
#         # Monthly check
#         current_month = timezone.now().strftime("%Y-%m")
#         package_limit = onboarding.package.seo_optimization_limit if onboarding.package else 5

#         # if task.month_year != current_month:
#         #     task.count_this_month = 0
#         #     task.month_year = current_month

#         completed_this_month = SEOTask.objects.filter(
#         user=user,
#         status='completed',
#         month_year=current_month,
#         task_type='seo_optimization'
#     ).count()

#         # Check if limit reached
#         if completed_this_month >= package_limit:
#             # Allow processing if we haven't reached exact limit
#             pages_remaining = package_limit - completed_this_month
#             logger.warning(f"🚫 Pages_remaining {pages_remaining}, Package limit -- > {package_limit}, Completed_this month {completed_this_month} ")
#             if pages_remaining <= 0:

#                 logger.warning("🚫 SEO task limit reached for this month.")
#                 task.status = "skipped"
#                 task.save()
#                 return

#         # Get service areas
#         service_areas = onboarding.service_areas.all()
#         if not service_areas:
#             logger.warning("⚠️ No service areas found.")
#             task.status = "failed"
#             task.save()
#             return

#         # Get all services
#         services = Service.objects.filter(onboarding_form=onboarding)
#         if not services:
#             logger.warning("⚠️ No services found.")
#             task.status = "failed"
#             task.save()
#             return
        
#         # Get WordPress connection (using the original task's connection)
#         wp_conn = task.service_page.wordpress_connection if task.service_page else None
#         if not wp_conn:
#             logger.warning("⚠️ No WordPress connection found.")
#             task.status = "failed"
#             task.save()
#             return

#         # Process each service and area combination
#         for service in services:
#             # Get keywords for this specific service
#             keywords = list(service.keywords.values_list("keyword", flat=True))
            
#             if not keywords:
#                 logger.warning(f"⚠️ No keywords found for service: {service.service_name}")
#                 continue
            
#             for area in service_areas:


#                 # Check if we've reached the monthly limit
#                 if task.count_this_month >= package_limit:
#                     logger.warning("🚫 Monthly limit reached, stopping processing.")
#                     break
                
#                 # Generate page URL for this service-area combination
#                 page_slug = f"{slugify(service.service_name)}-in-{slugify(area.area_name)}"
#                 page_url = f"{wp_conn.site_url.rstrip('/')}/{page_slug}"
                
#                 logger.info(f"🔧 Processing service '{service.service_name}' for area '{area.area_name}'")
                
#                 # Check if this page already exists in WordPress
#                 page_exists = False
#                 existing_content = ""
                
#                 try:
#                     page_response = requests.get(page_url, timeout=20)
#                     if page_response.status_code == 200:
#                         page_exists = True
#                         existing_content = page_response.text
#                 except Exception:
#                     # Page doesn't exist or can't be accessed - that's OK, we'll create it
#                     page_exists = False
                
#                 # Determine which API to use
#                 if page_exists:
#                     logger.info(f"page exists {page_url}'")
#                     # Page exists, use optimization API
#                     api_url = f"{settings.AI_API_DOMAIN}/optimize_content"
#                     api_payload = {
#                         "content": existing_content,
#                         "keywords": keywords,
#                         "area": area.area_name
#                     }
#                 else:
#                     # Page doesn't exist, use content generation API
#                     api_url = f"{settings.AI_API_DOMAIN}/generate_content"
#                     api_payload = {
#                         "keywords": keywords,
#                         "area": area.area_name,
#                         "type": "service_area"
#                     }
                
#                 # Call the appropriate API
#                 api_response = requests.post(
#                     api_url,
#                     json=api_payload,
#                     timeout=60
#                 )

#                 if api_response.status_code != 200:
#                     logger.error(f"❌ API response error: {api_response.text}")
#                     continue

#                 optimized_data = api_response.json()
#                 optimized_content = optimized_data.get("content") or optimized_data.get("optimizedContent")
                
#                 if not optimized_content:
#                     logger.warning("⚠️ No optimized content received.")
#                     continue
                
#                 # Upload to WordPress
#                 try:
#                     final_url = upload_service_page_to_wordpress(
#                         task.service_page,  # Use the original service page for connection info
#                         optimized_content,
#                         service_name=service.service_name,
#                         area_name=area.area_name
#                     )
                    
#                     if final_url:
#                         # Create a new SEOTask for this service-area combination
#                         SEOTask.objects.create(
#                             user=user,
#                             service_page=task.service_page,  # Reference the original service page
#                             task_type='seo_optimization',
#                             optimized_content=optimized_content,
#                             ai_request_payload=api_payload,
#                             ai_response_payload=optimized_data,
#                             wp_page_url=final_url,
#                             status='completed',
#                             last_run=timezone.now(),
#                             next_run=timezone.now() + timedelta(
#                                 days=onboarding.package.interval if onboarding.package else 7
#                             ),
#                             count_this_month=1,
#                             month_year=current_month,
#                             is_active=True,
#                         )
                        
#                         task.count_this_month += 1
#                         logger.info(f"✅ Created/optimized page for {service.service_name} in {area.area_name}: {final_url}")
#                     else:
#                         logger.error(f"❌ Failed to upload page for {service.service_name} in {area.area_name}")
#                 except Exception as e:
#                     logger.exception(f"❌ WordPress upload failed: {str(e)}")
        
#         # Update original task status
#         task.status = "completed"
#         task.last_run = timezone.now()
#         task.month_year = current_month
#         task.save()

#         logger.info(f"✅ SEO Optimization Task {task.id} completed.")

#         # Create next scheduling task (only if we didn't reach the limit)
#         interval_days = onboarding.package.interval if onboarding.package else 7
#         new_next_run = timezone.now() + timedelta(days=interval_days)
#         if task.count_this_month < package_limit:
#             SEOTask.objects.create(
#                 user=user,
#                 service_page=task.service_page,
#                 task_type='seo_optimization',
#                 next_run=new_next_run,
#                 status='pending',
#                 count_this_month=task.count_this_month,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("✅ Created next SEO scheduling task.")
#         else:
#             SEOTask.objects.create(
#                 user=user,
#                 service_page=task.service_page,
#                 task_type='seo_optimization',
#                 next_run=None,
#                 status='pending',
#                 count_this_month=0,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("⏸️ Limit reached, next SEO task paused for this month.")

#     except Exception as e:
#         logger.exception(f"❌ Exception in SEO Optimization task: {str(e)}")
#         task.status = "failed"
#         task.ai_response_payload = {"error": str(e)}
#         task.save()


def run_seo_optimization(task):
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"🚀 Running SEO optimization task for Task ID {task.id}")
        user = task.user

        onboarding = OnboardingForm.objects.filter(user=user).first()
        if not onboarding:
            logger.warning("⚠️ No onboarding form found.")
            task.status = "failed"
            task.save()
            return
        
        # Monthly check
        current_month = timezone.now().strftime("%Y-%m")
        package_limit = onboarding.package.seo_optimization_limit if onboarding.package else 5

        completed_this_month = SEOTask.objects.filter(
            user=user,
            status='completed',
            month_year=current_month,
            task_type='seo_optimization'
        ).count()

        # Check if limit reached
        if completed_this_month >= package_limit:
            # Allow processing if we haven't reached exact limit
            pages_remaining = package_limit - completed_this_month
            logger.warning(f"🚫 Pages_remaining {pages_remaining}, Package limit -- > {package_limit}, Completed_this month {completed_this_month} ")
            if pages_remaining <= 0:
                logger.warning("🚫 SEO task limit reached for this month.")
                task.status = "skipped"
                task.save()
                return

        # Get business locations instead of service areas
        business_locations = BusinessLocation.objects.filter(onboarding_form=onboarding)
        if not business_locations:
            logger.warning("⚠️ No business locations found.")
            task.status = "failed"
            task.save()
            return

        # Get all services
        services = Service.objects.filter(onboarding_form=onboarding)
        if not services:
            logger.warning("⚠️ No services found.")
            task.status = "failed"
            task.save()
            return
        
        # Get WordPress connection (using the original task's connection)
        wp_conn = task.service_page.wordpress_connection if task.service_page else None
        if not wp_conn:
            logger.warning("⚠️ No WordPress connection found.")
            task.status = "failed"
            task.save()
            return

        # Process each service and business location combination
        for service in services:
            # Get keywords for this specific service
            keywords = list(service.keywords.values_list("keyword", flat=True))
            
            if not keywords:
                logger.warning(f"⚠️ No keywords found for service: {service.service_name}")
                continue
            
            for location in business_locations:
                # Extract service areas from business_service_areas JSON field
                business_service_areas = location.business_service_areas or []
                
                if not business_service_areas:
                    logger.warning(f"⚠️ No business service areas found for location: {location.location_name}")
                    continue
                
                # Process each service area within the business location
                for service_area in business_service_areas:
                    area_name = service_area.get('name', '').strip()
                    if not area_name:
                        logger.warning(f"⚠️ Invalid service area name in location: {location.location_name}")
                        continue

                    # Check if we've reached the monthly limit
                    if task.count_this_month >= package_limit:
                        logger.warning("🚫 Monthly limit reached, stopping processing.")
                        break
                    
                    # Generate page URL for this service-area combination
                    page_slug = f"{slugify(service.service_name)}-in-{slugify(area_name)}"
                    page_url = f"{wp_conn.site_url.rstrip('/')}/{page_slug}"
                    
                    logger.info(f"🔧 Processing service '{service.service_name}' for area '{area_name}' in location '{location.location_name}'")
                    
                    # Check if this page already exists in WordPress
                    page_exists = False
                    existing_content = ""
                    
                    try:
                        page_response = requests.get(page_url, timeout=20)
                        if page_response.status_code == 200:
                            page_exists = True
                            existing_content = page_response.text
                    except Exception:
                        # Page doesn't exist or can't be accessed - that's OK, we'll create it
                        page_exists = False
                    
                    # Determine which API to use
                    if page_exists:
                        logger.info(f"page exists {page_url}'")
                        # Page exists, use optimization API
                        api_url = f"{settings.AI_API_DOMAIN}/optimize_content"
                        api_payload = {
                            "content": existing_content,
                            "keywords": keywords,
                            "area": area_name
                        }
                    else:
                        # Page doesn't exist, use content generation API
                        api_url = f"{settings.AI_API_DOMAIN}/generate_content"
                        api_payload = {
                            "keywords": keywords,
                            "area": area_name,
                            "type": "service_area"
                        }
                    
                    # Call the appropriate API
                    api_response = requests.post(
                        api_url,
                        json=api_payload,
                        timeout=60
                    )

                    if api_response.status_code != 200:
                        logger.error(f"❌ API response error: {api_response.text}")
                        # continue
                        raise Exception(f"AI API failed with status {api_response.status_code}: {api_response.text}")


                    optimized_data = api_response.json()
                    optimized_content = optimized_data.get("content") or optimized_data.get("optimizedContent")
                    
                    if not optimized_content:
                        logger.warning("⚠️ No optimized content received.")
                        continue
                    
                    # Upload to WordPress
                    try:
                        final_url = upload_service_page_to_wordpress(
                            task.service_page,  # Use the original service page for connection info
                            optimized_content,
                            service_name=service.service_name,
                            area_name=area_name
                        )
                        
                        if final_url:
                            # Create a new SEOTask for this service-area combination
                            SEOTask.objects.create(
                                user=user,
                                service_page=task.service_page,  # Reference the original service page
                                task_type='seo_optimization',
                                optimized_content=optimized_content,
                                ai_request_payload=api_payload,
                                ai_response_payload=optimized_data,
                                wp_page_url=final_url,
                                status='completed',
                                last_run=timezone.now(),
                                next_run=timezone.now() + timedelta(
                                    days=onboarding.package.interval if onboarding.package else 7
                                ),
                                count_this_month=1,
                                month_year=current_month,
                                is_active=True,
                            )
                            
                            task.count_this_month += 1
                            logger.info(f"✅ Created/optimized page for {service.service_name} in {area_name}: {final_url}")
                        else:
                            logger.error(f"❌ Failed to upload page for {service.service_name} in {area_name}")
                    except Exception as e:
                        logger.exception(f"❌ WordPress upload failed: {str(e)}")
        
        # Update original task status
        task.status = "completed"
        task.last_run = timezone.now()
        task.failure_count = 0  # ← Reset on success
        task.last_failure_reason = None  # ← Clear failure reason
        task.month_year = current_month
        task.save()

        logger.info(f"✅ SEO Optimization Task {task.id} completed.")

        # Create next scheduling task (only if we didn't reach the limit)
        interval_days = onboarding.package.interval if onboarding.package else 7
        new_next_run = timezone.now() + timedelta(days=interval_days)
        if task.count_this_month < package_limit:
            SEOTask.objects.create(
                user=user,
                service_page=task.service_page,
                task_type='seo_optimization',
                next_run=new_next_run,
                status='pending',
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True,
            )
            logger.info("✅ Created next SEO scheduling task.")
        else:
            SEOTask.objects.create(
                user=user,
                service_page=task.service_page,
                task_type='seo_optimization',
                next_run=None,
                status='pending',
                count_this_month=0,
                month_year=current_month,
                is_active=True,
            )
            logger.info("⏸️ Limit reached, next SEO task paused for this month.")

    except Exception as e:
        logger.exception(f"❌ Exception in SEO Optimization task: {str(e)}")
        # task.status = "failed"
        # task.ai_response_payload = {"error": str(e)}
        # task.save()

        raise



# def run_keyword_optimization(task):
#     logger = logging.getLogger(__name__)
#     logger.info("🔍 Running keyword optimization task...")

#     try:
#         user = task.user
#         onboarding = OnboardingForm.objects.filter(user=user).first()
#         if not onboarding:
#             logger.warning(f"⚠️ No onboarding form found for user {user.email}")
#             task.status = "failed"
#             task.save()
#             return
        
#         # Monthly limit check
#         current_month = timezone.now().strftime("%Y-%m")
#         package_limit = onboarding.package.keyword_limit if onboarding.package else 5  # Default if missing

#         if task.month_year == current_month and task.count_this_month >= package_limit:
#             logger.warning(f"🚫 Keyword optimization limit reached for this month.")
#             task.status = "skipped"
#             task.next_run = None
#             task.save()

#             SEOTask.objects.create(
#                 user=user,
#                 task_type="keyword_optimization",
#                 status="pending",
#                 is_active=True,
#                 month_year=current_month,
#                 count_this_month=0,
#                 next_run=None,
#             )
#             logger.info("⏸️ Limit reached, next keyword task paused for this month.")
#             return

#         services = onboarding.services.all()
#         if not services:
#             logger.warning(f"⚠️ No services found for onboarding form {onboarding.id}")
#             task.status = "failed"
#             task.save()
#             return

#         for service in services:
#             keywords = list(service.keywords.values_list("keyword", flat=True))
#             if not keywords:
#                 logger.warning(f"⚠️ No keywords found for service {service.id}")
#                 continue

#             ai_payload = {"keywords": keywords}
#             try:
#                 response = requests.post(
#                     f"{settings.AI_API_DOMAIN}/keyword_suggestions_multiple",
#                     json=ai_payload,
#                     timeout=30
#                 )
#                 if response.status_code != 200:
#                     logger.warning(f"⚠️ AI response error for service {service.id}: {response.text}")
#                     continue

#                 try:
#                     data = response.json()
#                 except Exception as parse_error:
#                     logger.warning(f"⚠️ Failed to parse JSON for service {service.id}: {parse_error}")
#                     continue

#                 suggestions = data.get("suggested_keywords", {})

#                 if not isinstance(suggestions, dict):
#                     logger.warning(f"⚠️ Invalid AI response for service {service.id}: {suggestions}")
#                     continue

#                 for original_keyword, suggestion_list in suggestions.items():
#                     if not suggestion_list:
#                         logger.info(f"ℹ️ No suggestions returned for keyword '{original_keyword}'")
#                         continue

#                     # Pick keyword with highest search volume
#                     best_keyword = max(suggestion_list, key=lambda k: k.get("search_volume", 0))
#                     new_keyword = best_keyword["keyword"]

#                     if new_keyword and new_keyword != original_keyword:
#                         keyword_obj = Keyword.objects.filter(service=service, keyword=original_keyword).first()
#                         if keyword_obj:
#                             logger.info(f"🔄 Replacing keyword '{original_keyword}' with '{new_keyword}' (volume: {best_keyword['search_volume']})")
#                             keyword_obj.keyword = new_keyword
#                             keyword_obj.save()
#                             # Logic For Faq's 
#                             # KeywordQuestion.objects.filter(keyword=keyword_obj).delete()  # Clear old ones
#                             # try:
#                             #     questions = get_paa_questions(new_keyword)
#                             #     logger.info(f"scrapped questions: {questions} for {new_keyword}")
#                             #     for q in questions:
#                             #         KeywordQuestion.objects.create(keyword=keyword_obj, question=q)
#                             #     logger.info(f"Saved {len(questions)} questions for keyword: {new_keyword}")
#                             # except Exception as e:
#                             #     logger.error(f"Failed to save questions for keyword {new_keyword}: {str(e)}")
#                             #     continue
#                         else:
#                             logger.warning(f"⚠️ Keyword object not found for '{original_keyword}' in service {service.id}")
#                     else:
#                         logger.info(f"✅ Keeping keyword '{original_keyword}' as is (volume: {best_keyword['search_volume']})")
#                         # Logic For Faq's 
#                         # keyword_obj = Keyword.objects.filter(service=service, keyword=original_keyword).first()
#                         # if keyword_obj:
#                         #     logger.info(f"🔍 Found keyword object: {keyword_obj.keyword}, Checking if questions exist...")

#                         # if keyword_obj and not keyword_obj.questions.exists():
#                         #     try:
#                         #         questions = get_paa_questions(original_keyword)
#                         #         for q in questions:
#                         #             KeywordQuestion.objects.create(keyword=keyword_obj, question=q)
#                         #         logger.info(f"📝 Saved {len(questions)} PAA questions for existing keyword: {original_keyword}")
#                         #     except Exception as e:
#                         #         logger.error(f"⚠️ Failed to save questions for keyword {original_keyword}: {str(e)}")
#                         # else:
#                         #     if keyword_obj:
#                         #         logger.info(f"📌 Skipping PAA fetch — questions already exist for: {original_keyword}")

#             except Exception as e:
#                 logger.exception(f"❌ Failed optimizing keywords for service {service.id}: {e}")

#         # Mark task complete
#         task.status = "completed"
#         task.last_run = timezone.now()
#         task.next_run = timezone.now() + timedelta(days=onboarding.package.interval if onboarding.package else 7)
#         # task.next_run = timezone.now() + timezone.timedelta(minutes=3)
#         task.month_year = current_month
#         task.count_this_month = (task.count_this_month or 0) + 1
#         task.save()
#         logger.info(f"✅ Keyword optimization task {task.id} completed.")

#         # ✅ Create next task (Active or Paused based on usage)
#         if task.count_this_month <= package_limit:
#             SEOTask.objects.create(
#                 user=user,
#                 task_type="keyword_optimization",
#                 next_run=task.next_run,
#                 status="pending",
#                 count_this_month=task.count_this_month,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("✅ Created next keyword optimization task.")
#         else:
#             SEOTask.objects.create(
#                 user=user,
#                 task_type="keyword_optimization",
#                 next_run=None,
#                 status="pending",
#                 count_this_month=0,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("⏸️ Limit reached, next keyword task paused for this month.")

#     except Exception as e:
#         logger.exception(f"❌ Exception in run_keyword_optimization for task {task.id}: {str(e)}")
#         task.status = "failed"
#         task.ai_response_payload = {"error": str(e)}
#         task.save()



# def run_keyword_optimization(task):
#     logger = logging.getLogger(__name__)
#     logger.info("🔍 Running keyword optimization task with DataForSEO...")

#     try:
#         user = task.user
#         onboarding = OnboardingForm.objects.filter(user=user).first()
#         if not onboarding:
#             logger.warning(f"⚠️ No onboarding form found for user {user.email}")
#             task.status = "failed"
#             task.save()
#             return
        
#         # Monthly limit check
#         current_month = timezone.now().strftime("%Y-%m")
#         package_limit = onboarding.package.keyword_limit if onboarding.package else 5

#         if task.month_year == current_month and task.count_this_month >= package_limit:
#             logger.warning(f"🚫 Keyword optimization limit reached for this month.")
#             task.status = "skipped"
#             task.next_run = None
#             task.save()

#             SEOTask.objects.create(
#                 user=user,
#                 task_type="keyword_optimization",
#                 status="pending",
#                 is_active=True,
#                 month_year=current_month,
#                 count_this_month=0,
#                 next_run=None,
#             )
#             logger.info("⏸️ Limit reached, next keyword task paused for this month.")
#             return

#         services = onboarding.services.all()
#         if not services:
#             logger.warning(f"⚠️ No services found for onboarding form {onboarding.id}")
#             task.status = "failed"
#             task.save()
#             return

#         for service in services:
#             # Get all keyword objects for this service
#             keyword_objects = service.keywords.all()
#             if not keyword_objects:
#                 logger.warning(f"⚠️ No keywords found for service {service.id}")
#                 continue

#             # Get original keywords
#             original_keywords = [kw.keyword for kw in keyword_objects]
            
#             # Step 1: Get keyword suggestions
#             logger.info(f"📋 Getting suggestions for {len(original_keywords)} keywords")
#             suggestions_data = fetch_keyword_suggestions(original_keywords)
            
#             if not suggestions_data:
#                 logger.warning(f"⚠️ No suggestions returned from DataForSEO API for service {service.id}")
#                 continue

#             # Step 2: Extract all suggested keywords and get their metrics
#             all_suggested_keywords = []
#             for original_keyword, suggestions in suggestions_data.items():
#                 for suggestion in suggestions:
#                     if suggestion["keyword"] and suggestion["keyword"] not in all_suggested_keywords:
#                         all_suggested_keywords.append(suggestion["keyword"])
            
#             # Also include original keywords to compare
#             all_keywords_to_check = list(set(original_keywords + all_suggested_keywords))
            
#             logger.info(f"📊 Getting metrics for {len(all_keywords_to_check)} keywords")
#             all_metrics = fetch_keyword_metrics(all_keywords_to_check)
            
#             if not all_metrics:
#                 logger.warning(f"⚠️ No metrics returned from DataForSEO API")
#                 continue

#             # Step 3: Process each original keyword and find better alternatives
#             for keyword_obj in keyword_objects:
#                 original_keyword = keyword_obj.keyword
#                 original_metrics = all_metrics.get(original_keyword, {})
                
#                 # Get suggestions for this specific keyword
#                 keyword_suggestions = suggestions_data.get(original_keyword, [])
                
#                 if not keyword_suggestions:
#                     logger.info(f"ℹ️ No suggestions found for keyword '{original_keyword}'")
#                     continue
                
#                 # Find the best alternative
#                 best_alternative = find_best_keyword_alternative(
#                     keyword_suggestions, 
#                     original_keyword, 
#                     all_metrics
#                 )
                
#                 if best_alternative and best_alternative["keyword"] != original_keyword:
#                     # Check if the alternative is significantly better
#                     original_score = calculate_keyword_score(original_metrics)
#                     alternative_score = calculate_keyword_score(best_alternative["metrics"])

#                     # Handle cases where scores might be 0 or None
#                     if original_score == 0 and alternative_score == 0:
#                         logger.info(f"✅ Keeping '{original_keyword}' - both original and alternative have score 0")
#                         continue
#                     elif original_score == 0:
#                         improvement_ratio = float('inf')
#                     else:
#                         improvement_ratio = alternative_score / original_score

#                         # Only replace if significantly better (e.g., 20% improvement)
#                     if improvement_ratio >= 1.2:
#                         logger.info(f"🔄 Replacing '{original_keyword}' with '{best_alternative['keyword']}' "
#                                 f"(improvement: {improvement_ratio:.2f}x)")
                        
#                         keyword_obj.keyword = best_alternative["keyword"]
#                         keyword_obj.save()
                        
#                         # Save DataForSEO metrics for the new keyword
#                         DataForSEOKeywordData.objects.update_or_create(
#                             keyword=keyword_obj,
#                             defaults={
#                                 "search_volume": best_alternative["metrics"].get("search_volume", 0) or 0,
#                                 "competition": (best_alternative["metrics"].get("competition", 0) or 0) / 100.0,
#                                 "cpc": best_alternative["metrics"].get("cpc", 0) or 0,
#                             }
#                         )
#                     else:
#                         logger.info(f"✅ Keeping '{original_keyword}' - alternative not significantly better "
#                                    f"(improvement: {improvement_ratio:.2f}x)")
#                 else:
#                     logger.info(f"✅ Keeping '{original_keyword}' - no better alternative found")

#         # Mark task complete
#         task.status = "completed"
#         task.last_run = timezone.now()
#         task.next_run = timezone.now() + timedelta(days=onboarding.package.interval if onboarding.package else 7)
#         task.month_year = current_month
#         task.count_this_month = (task.count_this_month or 0) + 1
#         task.save()
#         logger.info(f"✅ Keyword optimization task {task.id} completed.")

#         # Create next task
#         if task.count_this_month < package_limit:
#             SEOTask.objects.create(
#                 user=user,
#                 task_type="keyword_optimization",
#                 next_run=task.next_run,
#                 status="pending",
#                 count_this_month=task.count_this_month,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("✅ Created next keyword optimization task.")
#         else:
#             SEOTask.objects.create(
#                 user=user,
#                 task_type="keyword_optimization",
#                 next_run=None,
#                 status="pending",
#                 count_this_month=0,
#                 month_year=current_month,
#                 is_active=True,
#             )
#             logger.info("⏸️ Limit reached, next keyword task paused for this month.")

#     except Exception as e:
#         logger.exception(f"❌ Exception in run_keyword_optimization for task {task.id}: {str(e)}")
#         task.status = "failed"
#         task.save()


# Task for all metrice of each keyword
def run_keyword_optimization(task):
    logger = logging.getLogger(__name__)
    logger.info("🔍 Running keyword optimization task with DataForSEO...")

    try:
        user = task.user
        onboarding = OnboardingForm.objects.filter(user=user).first()
        if not onboarding:
            logger.warning(f"⚠️ No onboarding form found for user {user.email}")
            task.status = "failed"
            task.save()
            return
        
        # Monthly limit check
        current_month = timezone.now().strftime("%Y-%m")
        package_limit = onboarding.package.keyword_limit if onboarding.package else 5

        if task.month_year == current_month and task.count_this_month >= package_limit:
            logger.warning(f"🚫 Keyword optimization limit reached for this month.")
            task.status = "skipped"
            task.next_run = None
            task.failure_count = 0  
            task.last_failure_reason = None

            task.save()

            SEOTask.objects.create(
                user=user,
                task_type="keyword_optimization",
                status="pending",
                is_active=True,
                month_year=current_month,
                count_this_month=0,
                next_run=None,
            )
            logger.info("⏸️ Limit reached, next keyword task paused for this month.")
            return

        services = onboarding.services.all()
        if not services:
            logger.warning(f"⚠️ No services found for onboarding form {onboarding.id}")
            task.status = "failed"
            task.save()
            return

        for service in services:
            # Get all keyword objects for this service
            keyword_objects = service.keywords.all()
            if not keyword_objects:
                logger.warning(f"⚠️ No keywords found for service {service.id}")
                continue

            # Get original keywords
            original_keywords = [kw.keyword for kw in keyword_objects]
            
            # Step 1: Get keyword suggestions
            logger.info(f"📋 Getting suggestions for {len(original_keywords)} keywords")
            suggestions_data = fetch_keyword_suggestions(original_keywords)
            
            if not suggestions_data:
                logger.warning(f"⚠️ No suggestions returned from DataForSEO API for service {service.id}")
                # Even if no suggestions, we can still get metrics for original keywords
                all_keywords_to_check = original_keywords
            else:
                # Extract all suggested keywords
                all_suggested_keywords = []
                for original_keyword, suggestions in suggestions_data.items():
                    if suggestions:
                        for suggestion in suggestions:
                            if suggestion.get("keyword") and suggestion.get("keyword") not in all_suggested_keywords:
                                all_suggested_keywords.append(suggestion.get("keyword"))
                
                # Include both original and suggested keywords
                all_keywords_to_check = list(set(original_keywords + all_suggested_keywords))
            
            # Step 2: Get metrics for ALL keywords
            logger.info(f"📊 Getting metrics for {len(all_keywords_to_check)} keywords")
            all_metrics = fetch_keyword_metrics(all_keywords_to_check)
            
            if not all_metrics:
                logger.warning(f"⚠️ No metrics returned from DataForSEO API")
                continue

            # Step 3: Store metrics for ALL original keywords (not wasting API calls!)
            store_keyword_metrics(keyword_objects, all_metrics)
            logger.info(f"💾 Stored metrics for {len(keyword_objects)} keywords")

            # Step 4: Only now process replacements if we have suggestions
            if suggestions_data:
                for keyword_obj in keyword_objects:
                    original_keyword = keyword_obj.keyword
                    original_metrics = all_metrics.get(original_keyword, {})
                    
                    # Get suggestions for this specific keyword
                    keyword_suggestions = suggestions_data.get(original_keyword, [])
                    
                    if not keyword_suggestions:
                        logger.info(f"ℹ️ No suggestions found for keyword '{original_keyword}'")
                        continue
                    
                    # Find the best alternative
                    best_alternative = find_best_keyword_alternative(
                        keyword_suggestions, 
                        original_keyword, 
                        all_metrics
                    )
                    
                    if best_alternative and best_alternative["keyword"] != original_keyword:
                        # Check if the alternative is significantly better
                        original_score = calculate_keyword_score(original_metrics)
                        alternative_score = calculate_keyword_score(best_alternative["metrics"])
                        
                        # Handle cases where scores might be 0 or None
                        if original_score == 0 and alternative_score == 0:
                            logger.info(f"✅ Keeping '{original_keyword}' - both scores are 0")
                            continue
                        elif original_score == 0:
                            improvement_ratio = float('inf')
                        else:
                            improvement_ratio = alternative_score / original_score
                        
                        # Only replace if significantly better (e.g., 20% improvement)
                        if improvement_ratio >= 1.2:
                            logger.info(f"🔄 Replacing '{original_keyword}' with '{best_alternative['keyword']}' "
                                       f"(improvement: {improvement_ratio:.2f}x)")
                            
                            # Store metrics for the NEW keyword before replacing
                            new_keyword_obj, created = Keyword.objects.get_or_create(
                                service=service,
                                keyword=best_alternative["keyword"],
                                defaults={
                                    'clicks': 0,
                                    'impressions': 0,
                                    'average_position': None,
                                    'last_updated': timezone.now()
                                }
                            )
                            
                            if created:
                                logger.info(f"📝 Created new keyword: '{best_alternative['keyword']}'")
                            
                            # Update the DataForSEO data for the new keyword
                            DataForSEOKeywordData.objects.update_or_create(
                                keyword=new_keyword_obj,
                                defaults={
                                    "search_volume": best_alternative["metrics"].get("search_volume", 0) or 0,
                                    "competition": (best_alternative["metrics"].get("competition", 0) or 0) / 100.0,
                                    "competition_index": best_alternative["metrics"].get("competition", 0),
                                    "competition_level": best_alternative["metrics"].get("competition_level"),
                                    "cpc": best_alternative["metrics"].get("cpc", 0) or 0,
                                    "low_bid": best_alternative["metrics"].get("low_bid"),
                                    "high_bid": best_alternative["metrics"].get("high_bid"),
                                }
                            )
                            
                            # Now replace the old keyword with the new one
                            # (You might want to archive the old keyword instead of deleting it)
                            keyword_obj.delete()  # Or set inactive, depending on your strategy
                            
                        else:
                            logger.info(f"✅ Keeping '{original_keyword}' - alternative not significantly better "
                                       f"(improvement: {improvement_ratio:.2f}x)")
                    else:
                        logger.info(f"✅ Keeping '{original_keyword}' - no better alternative found")
            else:
                logger.info("ℹ️ No keyword suggestions available, only metrics were stored")

        # Mark task complete
        task.status = "completed"
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=onboarding.package.interval if onboarding.package else 7)
        task.month_year = current_month
        task.count_this_month = (task.count_this_month or 0) + 1
        task.failure_count = 0  # ← RESET on success
        task.last_failure_reason = None  # ← Clear failure reason
        task.save()
        logger.info(f"✅ Keyword optimization task {task.id} completed.")

        # Create next task
        if task.count_this_month < package_limit:
            SEOTask.objects.create(
                user=user,
                task_type="keyword_optimization",
                next_run=task.next_run,
                status="pending",
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True,
            )
            logger.info("✅ Created next keyword optimization task.")
        else:
            SEOTask.objects.create(
                user=user,
                task_type="keyword_optimization",
                next_run=None,
                status="pending",
                count_this_month=0,
                month_year=current_month,
                is_active=True,
            )
            logger.info("⏸️ Limit reached, next keyword task paused for this month.")

    except Exception as e:
        logger.exception(f"❌ Exception in run_keyword_optimization for task {task.id}: {str(e)}")
        # task.status = "failed"
        # task.save()
        raise



# In your views.py or tasks.py (same file as run_keyword_optimization)

# utils/dataforseo_utils.py
def store_keyword_metrics(keyword_objects, all_metrics):
    """
    Store metrics for all keywords, not just the replaced ones
    """
    for keyword_obj in keyword_objects:
        keyword_text = keyword_obj.keyword
        metrics = all_metrics.get(keyword_text, {})
        
        if metrics:
            # Convert competition from 0-100 scale to 0-1 scale
            competition_index = metrics.get("competition")
            competition = competition_index / 100.0 if competition_index is not None else None
            
            DataForSEOKeywordData.objects.update_or_create(
                keyword=keyword_obj,
                defaults={
                    "search_volume": metrics.get("search_volume", 0) or 0,
                    "competition": competition,
                    "competition_index": competition_index,
                    "competition_level": metrics.get("competition_level"),
                    "cpc": metrics.get("cpc", 0) or 0,
                    "low_bid": metrics.get("low_bid"),
                    "high_bid": metrics.get("high_bid"),
                }
            )

def find_best_keyword_alternative(suggestions, original_keyword, all_metrics):
    """
    Find the best keyword alternative from suggestions
    Handles missing metrics gracefully
    """
    if not suggestions:
        return None
    
    best_alternative = None
    best_score = 0
    
    for suggestion in suggestions:
        suggested_keyword = suggestion.get("keyword")
        
        # Skip the original keyword and invalid suggestions
        if (not suggested_keyword or 
            suggested_keyword == original_keyword or
            suggested_keyword not in all_metrics):
            continue
        
        metrics = all_metrics.get(suggested_keyword, {})
        
        # Skip if we don't have proper metrics
        if not metrics or metrics.get("search_volume") is None:
            continue
            
        score = calculate_keyword_score(metrics)
        
        # Apply additional filters - handle None values
        search_volume = metrics.get("search_volume", 0) or 0
        competition = metrics.get("competition", 100) or 100
        
        if (search_volume >= 50 and  # Minimum search volume
            competition <= 70 and  # Maximum competition
            score > best_score):
            
            best_score = score
            best_alternative = {
                "keyword": suggested_keyword,
                "metrics": metrics,
                "score": score
            }
    
    return best_alternative

def calculate_keyword_score(metrics):
    """
    Calculate a score for a keyword based on SEO metrics
    Higher score = better keyword
    Handles None values gracefully
    """
    if not metrics:
        return 0
        
    # Handle None values by providing defaults
    search_volume = metrics.get("search_volume", 0) or 0
    competition = metrics.get("competition", 100) or 100  # 0-100, lower is better
    cpc = metrics.get("cpc", 0) or 0  # Lower is better
    
    # Ensure all values are numbers (not None)
    try:
        search_volume = float(search_volume)
        competition = float(competition)
        cpc = float(cpc)
    except (TypeError, ValueError):
        return 0
    
    # Normalize and weight the factors
    volume_score = min(search_volume / 5000, 1.0)  # Cap at 5000 searches = max score
    competition_score = 1.0 - (competition / 100.0)  # Invert competition
    
    # Handle CPC - if CPC is 0, give it max score, otherwise invert it
    if cpc == 0:
        cpc_score = 1.0
    else:
        cpc_score = 1.0 - min(cpc / 20.0, 1.0)  # Invert CPC
    
    # Weighted combination (adjust these weights based on your strategy)
    return (volume_score * 0.5 + competition_score * 0.3 + cpc_score * 0.2)

def run_gmb_post_creation(task):
    try:
        user = task.user
        onboarding = OnboardingForm.objects.filter(user=user).first()
        
        if not onboarding:
            logger.warning("⚠ No onboarding form found for GMB post creation.")
            task.status = "failed"
            task.save()
            return

        # Monthly check
        current_month = timezone.now().strftime("%Y-%m")
        package_limit = onboarding.package.gmb_post_limit if onboarding.package else 5  # Default limit
        
        if task.month_year != current_month:
            task.count_this_month = 0
            task.month_year = current_month

        # Check if limit reached
        if task.count_this_month >= package_limit:
            logger.warning("🚫 GMB post limit reached for this month.")
            task.status = "skipped"
            task.save()
            return

        # Get service areas for location
        service_areas = onboarding.service_areas.all()
        if not service_areas.exists():
            logger.warning("⚠ No service areas found for GMB post.")
            task.status = "failed"
            task.save()
            return
        
        area_names = list(service_areas.values_list("area_name", flat=True))
        primary_area = area_names[0]  # Use the first area as primary

        # Get all services and their keywords
        services = onboarding.services.all()
        
        # We'll create a separate post for each service
        for service in services:
            keywords = service.keywords.all()
            if not keywords.exists():
                logger.warning(f"⚠ No keywords found for service {service.service_name}")
                continue

            keyword_list = list(keywords.values_list("keyword", flat=True))
            
            # Get research questions for these keywords
            questions = KeywordQuestion.objects.filter(keyword__in=keywords)
            research_words = list(questions.values_list("question", flat=True))
            
            logger.info(f"🔑 Keywords for GMB post ({service.service_name}): {keyword_list}")
            logger.info(f"🧠 Research words: {research_words[:10]}...")

            # Prepare payload for AI API
            ai_payload = {
                "keywords": keyword_list,
                "research_words": research_words,
                "area": primary_area,
                "type": "gmb_post"
            }

            # Call AI API
            try:
                response = requests.post(
                    f"{settings.AI_API_DOMAIN}/generate_content",
                    json=ai_payload,
                    timeout=60
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ AI API error for service {service.service_name}: {response.text}")
                    continue
                
                data = response.json()
                post_content = data.get("content", "").strip()
                logger.info(f"Found --------------- Content {post_content}")
                
                if not post_content:
                    logger.warning(f"⚠ Empty content received for service {service.service_name}")
                    continue

                # Save the GMB post
                GMBPost.objects.create(
                    seo_task=task,
                    content=post_content,
                    area=primary_area,
                    keywords=keyword_list,
                    research_words=research_words
                )

                logger.info(f"✅ GMB post created for service {service.service_name}")

            except Exception as e:
                logger.error(f"❌ Error creating GMB post for service {service.service_name}: {str(e)}")
                continue

        # Update task status
        task.ai_request_payload = ai_payload  # Save the last payload (for debugging)
        task.ai_response_payload = data if 'data' in locals() else None
        task.status = "completed"
        task.last_run = timezone.now()
        task.next_run = timezone.now() + timedelta(days=onboarding.package.interval if onboarding.package else 7)
        task.count_this_month += 1
        task.save()

        # Create next task if limit not reached
        if task.count_this_month < package_limit:
            SEOTask.objects.create(
                user=user,
                service_page=task.service_page,
                task_type='gmb_post',
                next_run=task.next_run,
                status='pending',
                count_this_month=task.count_this_month,
                month_year=current_month,
                is_active=True
            )
            logger.info("✅ Created next GMB post task")
        else:
            SEOTask.objects.create(
                user=user,
                service_page=task.service_page,
                task_type='gmb_post',
                next_run=None,
                status='pending',
                count_this_month=0,
                month_year=current_month,
                is_active=True
            )
            logger.info("⏸ GMB post limit reached, next task paused")

    except Exception as e:
        logger.exception(f"❌ Exception in run_gmb_post_creation: {str(e)}")
        task.status = "failed"
        task.ai_response_payload = {"error": str(e)}
        task.save()


# class StopAutomation(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         user = request.user
#         action = request.data.get("action")

#         if not action:
#             return Response({"success": False, "message": "action is required."}, status=400)

#         task_type_map = {
#             "keywords": "keyword_optimization",
#             "blog": "blog_writing",
#             "seo": "seo_optimization",
#             "gmb_post" : "gmb_post"
#         }

#         task_type = task_type_map.get(action)
#         if not task_type:
#             return Response({"success": False, "message": "Invalid action."}, status=400)
#         tasks = SEOTask.objects.filter(user=user, task_type=task_type, is_active=True)
#         if not tasks.exists():
#             return Response({"success": False, "message": f"No active {action} tasks found for user."}, status=404)

#         tasks.update(is_active=False)
#         return Response({"success": True, "message": f"{action.capitalize()} stopped successfully."})
    


# class StartAutomation(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         user = request.user
#         action = request.data.get("action")

#         if not action:
#             return Response({"success": False, "message": "Action is required."}, status=400)

#         valid_actions = {
#             "blog": "blog_writing",
#             "seo": "seo_optimization",
#             "keywords": "keyword_optimization",
#             "gmb_post" : "gmb_post"
#         }

#         task_type = valid_actions.get(action)
#         if not task_type:
#             return Response({"success": False, "message": "Invalid action provided."}, status=400)

#         # Get all inactive tasks of that type for the user
#         tasks = SEOTask.objects.filter(user=user, task_type=task_type, is_active=False)
#         if not tasks.exists():
#             return Response({"success": False, "message": f"No inactive {action} tasks found for user."}, status=404)

#         # Activate all those tasks
#         tasks.update(is_active=True)

#         return Response({"success": True, "message": f"{action.capitalize()} automation started successfully."})


class AutomationToggleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        task_type_map = {
            "keywords": "keyword_optimization",
            "blog": "blog_writing",
            "seo": "seo_optimization",
            "gmb_post": "gmb_post",
        }

        updates = []
        for key, task_type in task_type_map.items():
            if key in request.data:  # Only process keys that are sent
                value = request.data.get(key)

                if isinstance(value, bool):  # Must be True/False
                    tasks = SEOTask.objects.filter(user=user, task_type=task_type)

                    if tasks.exists():
                        tasks.update(is_active=value)
                        state = "started" if value else "stopped"
                        updates.append(f"{key} {state}")
                    else:
                        updates.append(f"No {key} tasks found")
                else:
                    updates.append(f"{key} must be true/false")

        return Response({"success": True, "updates": updates})
    
    def get(self, request):
        user = request.user

        task_type_map = {
            "keywords": "keyword_optimization",
            "blog": "blog_writing",
            "seo": "seo_optimization",
            "gmb_post": "gmb_post",
        }

        status_data = {}
        for key, task_type in task_type_map.items():
            tasks = SEOTask.objects.filter(user=user, task_type=task_type)
            if tasks.exists():
                status_data[key] = tasks.first().is_active
            else:
                status_data[key] = None  # No tasks found

        return Response({"success": True, "status": status_data})


# Get Apis ---------------------------
class MyServiceAreasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        onboarding = request.user.onboardingform.first()
        if not onboarding:
            return Response({"success": False, "message": "Onboarding not found.", "data": []})

        service_areas = onboarding.service_areas.all()
        serializer = ServiceAreaSerializer(service_areas, many=True)
        return Response({"success": True, "message": "Service areas retrieved successfully.", "data": serializer.data})




from rest_framework.pagination import PageNumberPagination
# class MyKeywordsView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         onboarding = request.user.onboardingform.first()
#         if not onboarding:
#             return Response({"success": False, "message": "Onboarding not found.", "data": []})

#         keywords = Keyword.objects.filter(service__onboarding_form=onboarding)
#         serializer = KeywordSerializer(keywords, many=True)
#         return Response({"success": True, "message": "Keywords retrieved successfully.", "data": serializer.data})




# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_keyword_metrics(request):
#     """
#     Get raw keyword metrics for dashboard
#     """
#     try:
#         keywords = Keyword.objects.filter(
#         service__onboarding_form__user=request.user
#         ).prefetch_related('dataforseo_data')
        
#         metrics = []
#         for keyword in keywords:
#             data = keyword.dataforseo_data.last()  # since it's a queryset
#             if data:
#                 metrics.append({
#                     'keyword': keyword.keyword,
#                     'clicks': keyword.clicks,
#                     'impressions': keyword.impressions,
#                     'ctr': keyword.ctr,
#                     'search_volume': data.search_volume,
#                     'competition': data.competition,
#                     'cpc': data.cpc,
#                     'last_updated': data.last_updated
#                 })

        
#         return Response({
#             'metrics': metrics,
#             'total_keywords': len(metrics)
#         })
        
#     except Exception as e:
#         logger.error(f"Error getting keyword metrics: {str(e)}")
#         return Response({
#             'error': 'Failed to get keyword metrics'
#         }, status=500)




# # update1
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.paginator import Paginator, EmptyPage
import logging

logger = logging.getLogger(__name__)

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        # Get the originally requested page number from query params
        try:
            requested_page = int(self.request.query_params.get(self.page_query_param, 1))
        except (TypeError, ValueError):
            requested_page = 1
            
        total_pages = self.page.paginator.num_pages
        
        # Calculate next and previous as boolean values
        has_next = requested_page < total_pages
        has_previous = requested_page > 1 and requested_page <= total_pages + 1
            
        return Response({
            "success": True,
            "message": "Keywords retrieved successfully.",
            "data": data,
            "pagination": {
                "count": self.page.paginator.count,
                "next": has_next,  # Boolean value
                "previous": has_previous,  # Boolean value
                "current_page": requested_page,
                "total_pages": total_pages,
                "page_size": self.page_size
            }
        })
    
    def paginate_queryset(self, queryset, request, view=None):
        """
        Custom pagination method that returns empty list for invalid pages
        """
        self.request = request
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            page_number = 1

        try:
            self.page = paginator.page(page_number)
        except EmptyPage:
            # Create a dummy page object with correct counts
            class DummyPage:
                def __init__(self, paginator):
                    self.paginator = paginator
                    self.object_list = []
                    
            class DummyPaginator:
                def __init__(self, count, num_pages):
                    self.count = count
                    self.num_pages = num_pages
                    
            self.page = DummyPage(DummyPaginator(paginator.count, paginator.num_pages))
            return []
        
        return list(self.page)

class MyKeywordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        onboarding = request.user.onboardingform.first()
        if not onboarding:
            return Response({"success": False, "message": "Onboarding not found.", "data": []})

        keywords = Keyword.objects.filter(service__onboarding_form=onboarding)
        
        # Add pagination
        paginator = CustomPagination()
        paginated_keywords = paginator.paginate_queryset(keywords, request)
        serializer = KeywordSerializer(paginated_keywords, many=True)
        
        return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_keyword_metrics(request):
    """
    Get raw keyword metrics for dashboard with pagination
    """
    try:
        keywords = Keyword.objects.filter(
            service__onboarding_form__user=request.user
        ).prefetch_related('dataforseo_data')
        
        # Get pagination parameters
        try:
            page_size = int(request.GET.get('page_size', 10))
        except (TypeError, ValueError):
            page_size = 10
            
        try:
            page_number = int(request.GET.get('page', 1))
        except (TypeError, ValueError):
            page_number = 1
        
        # Create paginator
        paginator = Paginator(keywords, page_size)
        total_count = paginator.count
        total_pages = paginator.num_pages
        
        # Get the requested page data
        try:
            current_page = paginator.page(page_number)
            paginated_keywords = current_page.object_list
        except EmptyPage:
            # If page is invalid, return empty data
            paginated_keywords = []
        
        metrics = []
        for keyword in paginated_keywords:
            data = keyword.dataforseo_data.last()
            if data:
                metrics.append({
                    'keyword': keyword.keyword,
                    'clicks': keyword.clicks,
                    'impressions': keyword.impressions,
                    'ctr': keyword.ctr,
                    'search_volume': data.search_volume,
                    'competition': data.competition,
                    'cpc': data.cpc,
                    'last_updated': data.last_updated
                })

        # Calculate next and previous as boolean values
        has_next = page_number < total_pages
        has_previous = page_number > 1 and page_number <= total_pages + 1

        return Response({
            'metrics': metrics,
            'total_keywords': len(metrics),
            'pagination': {
                'count': total_count,
                'next': has_next,  # Boolean value
                'previous': has_previous,  # Boolean value
                'current_page': page_number,
                'total_pages': total_pages,
                'page_size': page_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting keyword metrics: {str(e)}")
        return Response({
            'error': 'Failed to get keyword metrics'
        }, status=500)





class MyBlogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request,pk = None):
        user = request.user
        if pk:
            blog = get_object_or_404(Blog, id=pk, seo_task__user=user)
            serializer = BlogSerializer(blog)
            return Response({
                "success": True,
                "message": "Blog retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        blogs = Blog.objects.filter(seo_task__user=user)
        serializer = BlogSerializer(blogs, many=True)
        return Response({"success": True, "message": "Blogs retrieved successfully.", "data": serializer.data,"count": blogs.count(), })
    

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Blog
from .serializers import BlogEditSerializer
import requests
from bs4 import BeautifulSoup

class BlogEditView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, blog_id):
        blog = get_object_or_404(Blog, id=blog_id, seo_task__user=request.user)
        serializer = BlogEditSerializer(blog, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update local DB first
        updated_blog = serializer.save()
        
        # Then update WordPress via API
        wp_conn = blog.seo_task.service_page.wordpress_connection
        update_response = self.update_blog_on_wordpress(updated_blog, wp_conn)
        
        if update_response.status_code in [200, 201]:
            return Response({
                "success": True,
                "message": "Blog updated successfully",
                "data": BlogEditSerializer(updated_blog).data
            })
        
        return Response({
            "success": False,
            "message": "WordPress update failed",
            "wordpress_error": update_response.json()
        }, status=status.HTTP_400_BAD_REQUEST)
    def update_blog_on_wordpress(self, blog, wp_conn):
        headers = {
            'Authorization': f'Basic {wp_conn.access_token}',
            'Content-Type': 'application/json',
        }
        
        # Parse existing HTML
        soup = BeautifulSoup(blog.content, 'html.parser')
        
        # Get the new title from serializer (might be updated or same as before)
        new_title = blog.title
        
        # Update the HTML structure properly:
        # 1. Remove all existing titles
        for title_tag in soup.find_all('title'):
            title_tag.decompose()
        
        # 2. Add the new title
        new_title_tag = soup.new_tag('title')
        new_title_tag.string = new_title
        soup.head.append(new_title_tag)
        
        # 3. Update h1 if exists (optional but recommended)
        h1_tag = soup.find('h1')
        if h1_tag:
            h1_tag.string = new_title
        
        # Prepare update data
        update_data = {
            "title": new_title,
            "content": str(soup),  # Use the modified HTML
            "status": "publish"
        }
    
    # Handle category if needed
        if blog.category:
            category_id = self.get_or_create_category(wp_conn, blog.category)
            if category_id:
                update_data["categories"] = [category_id]
        
        response = requests.post(
            f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/posts/{blog.wp_post_id}",
            headers=headers,
            json=update_data
        )
    
        return response

    def get_or_create_category(self, wp_conn, category_name):
        """Helper function to get or create WordPress category"""
        headers = {
            'Authorization': f'Basic {wp_conn.access_token}',
            'Content-Type': 'application/json',
        }
        
        # First try to find existing category
        search_response = requests.get(
            f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/categories?search={category_name}",
            headers=headers
        )
        
        if search_response.status_code == 200 and search_response.json():
            return search_response.json()[0]['id']
        
        # Create new category if not found
        create_response = requests.post(
            f"{wp_conn.site_url.rstrip('/')}/wp-json/wp/v2/categories",
            headers=headers,
            json={"name": category_name}
        )
        
        if create_response.status_code in [200, 201]:
            return create_response.json().get('id')
        
        return None
    
# ----------------

# admin 
class AdminClientListAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.filter(user_type='user')
        serializer = AdminClientDetailSerializer(users, many=True)
        return Response({
            "count": users.count(),   # 👈 added
            "data": serializer.data
        })


from django.db.models import Sum
class SEOStatsAPIView(APIView):
    permission_classes = [IsAdminUser]  # Only admin can access

    def get(self, request):
        # Total counts
        total_users = User.objects.filter(user_type="user").count()
        total_blogs = Blog.objects.count()
        total_service_page = SEOTask.objects.filter(task_type = "seo_optimization").count()

        # Top keywords by impressions
        top_keywords = (
            Keyword.objects.annotate(total_impressions=Sum("impressions"))
            .order_by("-total_impressions")[:5]  # Top 5
            .values("keyword", "clicks", "impressions")
        )

        # Latest blogs (last 5)
        latest_blogs = Blog.objects.order_by("-created_at")[:5]
        latest_blogs_data = BlogSerializer(latest_blogs, many=True).data

        return Response({
            "total_users": total_users,
            "total_blogs": total_blogs,
            "total_service_page": total_service_page,
            "top_keywords": list(top_keywords),
            "latest_blogs": latest_blogs_data
        })


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import OnboardingForm, WordPressConnection, Package
# if you have JobOnboardingForm model, import it here
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import OnboardingForm, WordPressConnection, Package
# if you have JobOnboardingForm model, import it here


from django.utils import timezone
from g_matrix.models import SearchConsoleToken, GoogleAnalyticsToken, GoogleBusinessToken


def is_valid_google_analytics(user):
    token = GoogleAnalyticsToken.objects.filter(user=user).first()
    if not token:
        return False

    # Check if token expired
    if token.token_expiry and token.token_expiry <= timezone.now():
        # 👇 Here you could attempt a refresh with the refresh_token
        # If refresh fails, return False
        return False
    return True


def is_valid_search_console(user):
    
    token = SearchConsoleToken.objects.filter(user=user).first()
    if not token:
        return False

    # If you store expiry inside credentials JSON
    expiry = token.credentials.get("expiry") if token.credentials else None
    if expiry and timezone.now() >= timezone.datetime.fromisoformat(expiry):
        return False
    return True


def is_valid_business_profile(user):
    token = GoogleBusinessToken.objects.filter(user=user).first()
    if not token:
        return False

    expiry = token.credentials.get("expiry") if token.credentials else None
    if expiry and timezone.now() >= timezone.datetime.fromisoformat(expiry):
        return False
    return True



class UserSetupStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        print(user.email)

        # Check WordPress connection
        wp_connected = WordPressConnection.objects.filter(user=user).exists()
        business_details = BusinessDetails.objects.filter(user=user).exists()

        # Check onboarding form
        onboarding_form = OnboardingForm.objects.filter(user=user).first()
        onboarding_submitted = onboarding_form is not None

        # Check jobboarding (assuming JobOnboardingForm exists)
        try:
            from job.models import JobOnboardingForm
            jobboarding_submitted = JobOnboardingForm.objects.filter(user=user).exists()
        except ImportError:
            jobboarding_submitted = False  # If no JobOnboardingForm model
        # Check package subscribed
                # Default values
        package = None
        package_subscribed = False

        user_subscription = getattr(user, "usersubscription", None)

        if user_subscription:
            print("DEBUG subscription status:", repr(user_subscription.status))  # <-- helps check exact value

            if str(user_subscription.status).strip().lower() == "active":
                if user_subscription.package:
                    package = user_subscription.package
                    package_subscribed = True


        # ✅ Token validity checks
        search_console_connected = is_valid_search_console(user)
        analytics_connected = is_valid_google_analytics(user)
        business_connected = is_valid_business_profile(user)


        data = {
            "user": {
                "id": user.id,
                "email": user.email,
                # "username": user.username,
                "full_name": getattr(user, "full_name", None),  # if exists
            },
            "status": {
                "wordpress_connected": wp_connected,
                "onboarding_submitted": onboarding_submitted,
                "jobboarding_submitted": jobboarding_submitted,
                "package_subscribed": package_subscribed,
                "search_console_connected": search_console_connected,
                "analytics_connected": analytics_connected,
                "business_profile_connected": business_connected,
                "business_details_connected": business_details
            },
        }

        # Add package details if subscribed
        if package:
            data["package"] = {
                "name": package.name,
                "interval_days": package.interval,
                "blog_limit": package.blog_limit,
                "keyword_limit": package.keyword_limit,
                "seo_optimization_limit": package.seo_optimization_limit,
                "price": str(package.price),
            }
        else:
            data["package"] = None

        return Response(data)



class BusinessDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve business details for logged-in user"""
        try:
            business = request.user.business_details  # via related_name
            serializer = BusinessDetailsSerializer(business)
            return Response(serializer.data, status=200)
        except BusinessDetails.DoesNotExist:
            return Response({"error": "No business details found."}, status=404)

    def post(self, request):
        """Create or update business details for logged-in user"""
        try:
            business = request.user.business_details
            serializer = BusinessDetailsSerializer(business, data=request.data, partial=True)
        except BusinessDetails.DoesNotExist:
            serializer = BusinessDetailsSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
