"""
Cross-Portal Property Deduplication & Entity Resolution Engine
Merges duplicate listings across Domain, Realestate.com.au, Rent.com.au, and Homely
into a single authoritative CanonicalListing with unified sources.
"""

from typing import List, Dict, Any, Optional
import math
from .models import CanonicalListing, PortalSource, InspectionSlot

class DeduplicationEngine:
    """
    Deduplicates listings from multiple portals using address hashing
    and spatial proximity fallback.
    """

    def __init__(self):
        # Maps canonical_hash -> CanonicalListing
        self.indexed_listings: Dict[str, CanonicalListing] = {}

    def add(self, listing: CanonicalListing) -> CanonicalListing:
        """
        Ingests a listing. If a duplicate exists, merges metadata and portal sources;
        otherwise records as a new canonical entry.
        """
        canonical_key = listing.address.generate_canonical_key()
        
        # 1. Exact address key match
        if canonical_key in self.indexed_listings:
            existing = self.indexed_listings[canonical_key]
            return self._merge_listings(existing, listing)

        # 2. Spatial proximity fallback (if both listings have coordinates)
        if listing.address.lat and listing.address.lng:
            for existing in self.indexed_listings.values():
                if existing.address.lat and existing.address.lng:
                    dist_meters = self._haversine_distance(
                        listing.address.lat, listing.address.lng,
                        existing.address.lat, existing.address.lng
                    )
                    # Within 25 meters and identical beds/baths = same property
                    if (dist_meters < 25 and 
                        listing.features.beds == existing.features.beds and 
                        listing.features.baths == existing.features.baths):
                        return self._merge_listings(existing, listing)

        # New property
        self.indexed_listings[canonical_key] = listing
        return listing

    def process_batch(self, listings: List[CanonicalListing]) -> List[CanonicalListing]:
        """Processes a batch of raw scraped listings and returns unique canonical listings."""
        for item in listings:
            self.add(item)
        return list(self.indexed_listings.values())

    def _merge_listings(self, primary: CanonicalListing, incoming: CanonicalListing) -> CanonicalListing:
        """Merges two listings for the same physical property."""
        # 1. Merge portal sources
        existing_portals = {s.portal for s in primary.sources}
        for src in incoming.sources:
            if src.portal not in existing_portals:
                primary.sources.append(src)
                existing_portals.add(src.portal)

        # 2. Upgrade image if primary doesn't have one or incoming is higher resolution
        if not primary.image_url and incoming.image_url:
            primary.image_url = incoming.image_url
        if incoming.extra_images:
            primary.extra_images = list(set(primary.extra_images + incoming.extra_images))

        # 3. Merge inspection dates without duplicates
        existing_inspections = {insp.start_time for insp in primary.inspections}
        for insp in incoming.inspections:
            if insp.start_time and insp.start_time not in existing_inspections:
                primary.inspections.append(insp)
                existing_inspections.add(insp.start_time)

        # Sort inspections chronologically
        primary.inspections.sort(key=lambda x: x.start_time)

        # 4. Feature union (if one portal detected pets or pool, mark it)
        if incoming.features.pets_allowed:
            primary.features.pets_allowed = 1
        if incoming.features.has_pool:
            primary.features.has_pool = True
        if incoming.features.has_aircon:
            primary.features.has_aircon = True
        if incoming.features.has_yard:
            primary.features.has_yard = True
        primary.features.tags = list(set(primary.features.tags + incoming.features.tags))

        # 5. Price history tracking
        if incoming.price.weekly and primary.price.weekly:
            if incoming.price.weekly != primary.price.weekly:
                primary.price_history.append({
                    "date": incoming.last_seen,
                    "price": incoming.price.weekly,
                    "source": incoming.sources[0].portal if incoming.sources else "portal"
                })
                # Set price to lowest active price if discrepancy
                primary.price.weekly = min(primary.price.weekly, incoming.price.weekly)

        # 6. Fill in missing coordinates
        if not primary.address.lat and incoming.address.lat:
            primary.address.lat = incoming.address.lat
            primary.address.lng = incoming.address.lng

        # 7. Update last_seen
        primary.last_seen = incoming.last_seen

        return primary

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two GPS coordinates in meters."""
        r = 6371000 # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0)**2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c
