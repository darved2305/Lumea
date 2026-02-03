"""
Pharmacy Locator Service

Integrates with Google Places API (or other map APIs)
to find nearby pharmacies, Jan Aushadhi Kendras, and medical stores.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
import aiohttp
from datetime import datetime

from app.settings import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import PharmacyClick

logger = logging.getLogger(__name__)


# Cache for pharmacy results (simple in-memory cache)
_pharmacy_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 3600  # 1 hour


class PharmacyLocator:
    """
    Finds nearby pharmacies using Google Places API.
    
    Features:
    - Search for generic pharmacies, Jan Aushadhi Kendras, PMBI stores
    - Get place details (address, phone, hours, directions)
    - Track clicks for analytics
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.api_key = getattr(settings, 'google_places_api_key', None)
        self.base_url = "https://maps.googleapis.com/maps/api/place"
    
    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 5000,
        pharmacy_type: str = "all",
        page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for nearby pharmacies.
        
        Args:
            latitude: User latitude
            longitude: User longitude
            radius_meters: Search radius (default 5km)
            pharmacy_type: "all", "jan_aushadhi", "generic"
            page_token: For pagination
            
        Returns:
            Dict with pharmacies list and pagination info
        """
        if not self.api_key:
            return await self._get_mock_pharmacies(latitude, longitude, pharmacy_type)
        
        # Build search query based on type
        keyword = self._get_search_keyword(pharmacy_type)
        
        # Check cache
        cache_key = f"{latitude:.4f},{longitude:.4f},{radius_meters},{pharmacy_type}"
        if cache_key in _pharmacy_cache and not page_token:
            cached = _pharmacy_cache[cache_key]
            if datetime.now().timestamp() - cached['timestamp'] < CACHE_TTL:
                return cached['data']
        
        try:
            pharmacies = await self._search_google_places(
                latitude, longitude, radius_meters, keyword, page_token
            )
            
            # Cache results
            if not page_token:
                _pharmacy_cache[cache_key] = {
                    'data': pharmacies,
                    'timestamp': datetime.now().timestamp()
                }
            
            return pharmacies
            
        except Exception as e:
            logger.error(f"Google Places API error: {e}")
            return await self._get_mock_pharmacies(latitude, longitude, pharmacy_type)
    
    async def _search_google_places(
        self,
        latitude: float,
        longitude: float,
        radius: int,
        keyword: str,
        page_token: Optional[str]
    ) -> Dict[str, Any]:
        """Call Google Places Nearby Search API."""
        url = f"{self.base_url}/nearbysearch/json"
        
        params = {
            'location': f"{latitude},{longitude}",
            'radius': radius,
            'keyword': keyword,
            'type': 'pharmacy',
            'key': self.api_key
        }
        
        if page_token:
            params['pagetoken'] = page_token
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
        
        if data.get('status') != 'OK' and data.get('status') != 'ZERO_RESULTS':
            logger.error(f"Google Places API error: {data.get('status')} - {data.get('error_message')}")
            raise Exception(f"API Error: {data.get('status')}")
        
        results = data.get('results', [])
        pharmacies = [self._format_place(place) for place in results]
        
        # Sort by distance (approximate)
        pharmacies = self._sort_by_distance(pharmacies, latitude, longitude)
        
        return {
            'pharmacies': pharmacies,
            'next_page_token': data.get('next_page_token'),
            'total': len(pharmacies)
        }
    
    async def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a pharmacy.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Dict with full place details
        """
        if not self.api_key:
            return self._get_mock_details(place_id)
        
        url = f"{self.base_url}/details/json"
        params = {
            'place_id': place_id,
            'fields': 'name,formatted_address,formatted_phone_number,opening_hours,geometry,rating,user_ratings_total,website,url',
            'key': self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    data = await response.json()
            
            if data.get('status') != 'OK':
                raise Exception(f"API Error: {data.get('status')}")
            
            result = data.get('result', {})
            return self._format_place_details(result, place_id)
            
        except Exception as e:
            logger.error(f"Place details error: {e}")
            return self._get_mock_details(place_id)
    
    async def log_pharmacy_click(
        self,
        user_id: UUID,
        place_id: str,
        action: str = "directions",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> None:
        """Log a pharmacy click for analytics."""
        if not self.db:
            return
        
        try:
            click = PharmacyClick(
                user_id=user_id,
                place_id=place_id,
                action=action,
                user_lat=latitude,
                user_lng=longitude
            )
            self.db.add(click)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log pharmacy click: {e}")
    
    def _get_search_keyword(self, pharmacy_type: str) -> str:
        """Get search keyword based on pharmacy type."""
        if pharmacy_type == "jan_aushadhi":
            return "Jan Aushadhi Kendra PMBI generic medicine"
        elif pharmacy_type == "generic":
            return "generic medicine pharmacy"
        else:
            return "pharmacy medical store chemist"
    
    def _format_place(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """Format Google Place result."""
        location = place.get('geometry', {}).get('location', {})
        
        # Check if it's a Jan Aushadhi Kendra
        name_lower = place.get('name', '').lower()
        is_jan_aushadhi = any(kw in name_lower for kw in [
            'jan aushadhi', 'janaushadhi', 'pmbi', 'pradhan mantri'
        ])
        
        return {
            'place_id': place.get('place_id'),
            'name': place.get('name'),
            'address': place.get('vicinity'),
            'latitude': location.get('lat'),
            'longitude': location.get('lng'),
            'rating': place.get('rating'),
            'total_ratings': place.get('user_ratings_total'),
            'is_open': place.get('opening_hours', {}).get('open_now'),
            'is_jan_aushadhi': is_jan_aushadhi,
            'photo_reference': place.get('photos', [{}])[0].get('photo_reference') if place.get('photos') else None
        }
    
    def _format_place_details(self, result: Dict[str, Any], place_id: str) -> Dict[str, Any]:
        """Format place details response."""
        location = result.get('geometry', {}).get('location', {})
        hours = result.get('opening_hours', {})
        
        return {
            'place_id': place_id,
            'name': result.get('name'),
            'address': result.get('formatted_address'),
            'phone': result.get('formatted_phone_number'),
            'website': result.get('website'),
            'google_maps_url': result.get('url'),
            'latitude': location.get('lat'),
            'longitude': location.get('lng'),
            'rating': result.get('rating'),
            'total_ratings': result.get('user_ratings_total'),
            'is_open': hours.get('open_now'),
            'hours': hours.get('weekday_text', []),
            'directions_url': f"https://www.google.com/maps/dir/?api=1&destination={location.get('lat')},{location.get('lng')}&destination_place_id={place_id}"
        }
    
    def _sort_by_distance(
        self,
        pharmacies: List[Dict[str, Any]],
        user_lat: float,
        user_lng: float
    ) -> List[Dict[str, Any]]:
        """Sort pharmacies by approximate distance."""
        import math
        
        def distance(p):
            if not p.get('latitude') or not p.get('longitude'):
                return float('inf')
            # Haversine-like approximation (good enough for sorting)
            dlat = (p['latitude'] - user_lat) * 111  # km per degree
            dlng = (p['longitude'] - user_lng) * 111 * math.cos(math.radians(user_lat))
            return math.sqrt(dlat**2 + dlng**2)
        
        return sorted(pharmacies, key=distance)
    
    async def _get_mock_pharmacies(
        self,
        latitude: float,
        longitude: float,
        pharmacy_type: str
    ) -> Dict[str, Any]:
        """Return mock pharmacies when API is not available."""
        mock_pharmacies = [
            {
                'place_id': 'mock_jan_aushadhi_1',
                'name': 'Jan Aushadhi Kendra - Government Medical Store',
                'address': 'Near District Hospital, Main Road',
                'latitude': latitude + 0.01,
                'longitude': longitude + 0.005,
                'rating': 4.5,
                'total_ratings': 120,
                'is_open': True,
                'is_jan_aushadhi': True,
                'photo_reference': None
            },
            {
                'place_id': 'mock_generic_1',
                'name': 'Generic Medicine Center',
                'address': 'Shop No. 5, Market Complex',
                'latitude': latitude - 0.008,
                'longitude': longitude + 0.012,
                'rating': 4.2,
                'total_ratings': 85,
                'is_open': True,
                'is_jan_aushadhi': False,
                'photo_reference': None
            },
            {
                'place_id': 'mock_pharmacy_1',
                'name': 'Apollo Pharmacy',
                'address': '123 MG Road, City Center',
                'latitude': latitude + 0.015,
                'longitude': longitude - 0.01,
                'rating': 4.0,
                'total_ratings': 230,
                'is_open': True,
                'is_jan_aushadhi': False,
                'photo_reference': None
            },
            {
                'place_id': 'mock_pmbi_1',
                'name': 'PMBI Jan Aushadhi Store',
                'address': 'Block A, Government Complex',
                'latitude': latitude - 0.02,
                'longitude': longitude - 0.015,
                'rating': 4.3,
                'total_ratings': 67,
                'is_open': False,
                'is_jan_aushadhi': True,
                'photo_reference': None
            }
        ]
        
        # Filter by type
        if pharmacy_type == "jan_aushadhi":
            mock_pharmacies = [p for p in mock_pharmacies if p['is_jan_aushadhi']]
        elif pharmacy_type == "generic":
            mock_pharmacies = [p for p in mock_pharmacies if not p['is_jan_aushadhi'] or 'generic' in p['name'].lower()]
        
        return {
            'pharmacies': mock_pharmacies,
            'next_page_token': None,
            'total': len(mock_pharmacies),
            'is_mock': True
        }
    
    def _get_mock_details(self, place_id: str) -> Dict[str, Any]:
        """Return mock details when API is not available."""
        return {
            'place_id': place_id,
            'name': 'Jan Aushadhi Kendra',
            'address': 'Near District Hospital, Main Road, City',
            'phone': '+91-XXXXXXXXXX',
            'website': None,
            'google_maps_url': f'https://www.google.com/maps/search/?api=1&query=Jan+Aushadhi+Kendra',
            'latitude': 28.6139,
            'longitude': 77.2090,
            'rating': 4.5,
            'total_ratings': 100,
            'is_open': True,
            'hours': [
                'Monday: 9:00 AM – 9:00 PM',
                'Tuesday: 9:00 AM – 9:00 PM',
                'Wednesday: 9:00 AM – 9:00 PM',
                'Thursday: 9:00 AM – 9:00 PM',
                'Friday: 9:00 AM – 9:00 PM',
                'Saturday: 9:00 AM – 6:00 PM',
                'Sunday: Closed'
            ],
            'directions_url': 'https://www.google.com/maps/dir/',
            'is_mock': True
        }
