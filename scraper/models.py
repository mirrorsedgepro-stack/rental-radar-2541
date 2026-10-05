"""
Canonical Data Models for Australian Rental & Property Scraper
Provides normalized, type-safe structures for real estate listings
across all Australian property portals.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import hashlib
import re

@dataclass
class PropertyAddress:
    street: str = ""
    suburb: str = ""
    state: str = "NSW"
    postcode: str = ""
    unit: Optional[str] = None
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

    @property
    def full_address(self) -> str:
        parts = []
        if self.unit:
            parts.append(f"{self.unit}/")
        if self.street:
            parts.append(self.street)
        parts.append(f", {self.suburb} {self.state} {self.postcode}".strip())
        return "".join(parts).strip(", ")

    def generate_canonical_key(self) -> str:
        """
        Generates a deterministic hash for deduplicating identical properties
        scraped from different portals (e.g. Domain vs Realestate.com.au).
        """
        # Normalize: remove unit punctuation, lowercase, collapse spaces
        clean_street = re.sub(r'[^a-z0-9]', '', self.street.lower())
        clean_suburb = re.sub(r'[^a-z0-9]', '', self.suburb.lower())
        clean_state = re.sub(r'[^a-z0-9]', '', self.state.lower())
        clean_postcode = re.sub(r'[^0-9]', '', self.postcode)
        
        raw_key = f"{clean_street}|{clean_suburb}|{clean_state}|{clean_postcode}"
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()[:16]

@dataclass
class PriceInfo:
    weekly: Optional[int] = None
    monthly: Optional[int] = None
    sale_price: Optional[int] = None
    raw_text: str = ""
    bond_amount: Optional[int] = None
    is_deposit_taken: bool = False
    is_contact_agent: bool = False

@dataclass
class PropertyFeatures:
    beds: int = 1
    baths: int = 1
    cars: int = 1
    prop_type: str = "House"  # House, Apartment, Unit, Townhouse, Villa, Studio, Duplex
    pets_allowed: int = 0      # 0 = Unknown/No, 1 = Allowed
    has_pool: bool = False
    has_aircon: bool = False
    has_yard: bool = False
    is_furnished: bool = False
    tags: List[str] = field(default_factory=list)

@dataclass
class InspectionSlot:
    start_time: str            # ISO-8601 string
    end_time: Optional[str] = None
    raw_text: str = ""

@dataclass
class PortalSource:
    portal: str                # e.g., "realestate.com.au", "domain.com.au", "rent.com.au"
    url: str
    external_id: str
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class CanonicalListing:
    id: str                    # Unique canonical identifier
    title: str
    address: PropertyAddress
    price: PriceInfo
    features: PropertyFeatures
    listing_type: str = "rent" # "rent" or "sale"
    description: str = ""
    image_url: str = ""
    extra_images: List[str] = field(default_factory=list)
    inspections: List[InspectionSlot] = field(default_factory=list)
    sources: List[PortalSource] = field(default_factory=list)
    status: str = "discovered" # discovered, watching, shortlisted, applied, leased
    is_new: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    price_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_db_dict(self) -> Dict[str, Any]:
        """Converts canonical listing to dictionary for database insertion."""
        feature_tags = list(self.features.tags)
        if self.features.pets_allowed:
            feature_tags.append("pets")
        if self.features.has_pool:
            feature_tags.append("pool")
        if self.features.has_aircon:
            feature_tags.append("aircon")
        if self.features.has_yard:
            feature_tags.append("yard")
        feature_tags = list(set(feature_tags))

        primary_url = self.sources[0].url if self.sources else ""
        primary_source = self.sources[0].portal if self.sources else "aggregator"
        primary_inspection = self.inspections[0].start_time if self.inspections else None
        price_num = self.price.sale_price if self.listing_type == "sale" else (self.price.weekly or 0)

        return {
            "id": self.id,
            "url": primary_url,
            "title": self.title or f"{self.address.street}, {self.address.suburb}",
            "street": self.address.street,
            "suburb": self.address.suburb,
            "state": self.address.state,
            "postcode": self.address.postcode,
            "price": price_num,
            "listing_type": self.listing_type,
            "beds": self.features.beds,
            "baths": self.features.baths,
            "cars": self.features.cars,
            "prop_type": self.features.prop_type,
            "image_url": self.image_url,
            "lat": self.address.lat,
            "lng": self.address.lng,
            "inspection_date": primary_inspection,
            "description": self.description,
            "source": primary_source,
            "status": self.status,
            "notes": "",
            "rating": 0,
            "is_favorite": 0,
            "is_new": self.is_new,
            "pets_allowed": self.features.pets_allowed,
            "features": feature_tags,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "price_history": self.price_history
        }
