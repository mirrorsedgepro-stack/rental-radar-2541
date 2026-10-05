"""
Australian Real Estate Scraper Architecture Package
"""

from .engine import AustralianRentalScraperEngine
from .deduplicator import DeduplicationEngine
from .models import CanonicalListing, PropertyAddress, PriceInfo, PropertyFeatures, PortalSource, InspectionSlot
from .normalizer import parse_australian_address, parse_rental_price, parse_sale_price, detect_property_features

def run_scraper_and_sync(
    suburb_or_city: str = "australia",
    state: str = "all",
    max_price: int = 550,
    listing_type: str = "rent"
):
    """Convenience runner that executes the multi-portal scraper and syncs to database."""
    import database
    database.init_db()
    settings = database.get_settings()
    webhook_url = settings.get("webhook_url", "")
    
    engine = AustralianRentalScraperEngine()
    listings = engine.crawl(
        suburb_or_city=suburb_or_city,
        state=state,
        max_price=max_price,
        listing_type=listing_type
    )
    result = engine.sync_to_database(listings, webhook_url=webhook_url)
    return result

__all__ = [
    "AustralianRentalScraperEngine",
    "DeduplicationEngine",
    "CanonicalListing",
    "PropertyAddress",
    "PriceInfo",
    "PropertyFeatures",
    "PortalSource",
    "InspectionSlot",
    "parse_australian_address",
    "parse_rental_price",
    "parse_sale_price",
    "detect_property_features",
    "run_scraper_and_sync"
]
