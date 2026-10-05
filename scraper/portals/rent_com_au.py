"""
Rent.com.au Portal Scraper
Extracts rental listings across Australia from Rent.com.au using structured JSON-LD schemas.
"""

import json
import logging
from bs4 import BeautifulSoup
from typing import List, Optional
from ..base import BasePortalScraper
from ..models import CanonicalListing, PropertyAddress, PriceInfo, PropertyFeatures, PortalSource, InspectionSlot
from ..normalizer import parse_rental_price, detect_property_features, parse_inspection_datetime, parse_australian_address

logger = logging.getLogger(__name__)

class RentComAuScraper(BasePortalScraper):
    PORTAL_NAME = "rent.com.au"
    BASE_URL = "https://www.rent.com.au"

    def scrape(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent"
    ) -> List[CanonicalListing]:
        """Scrapes listings from Rent.com.au for given location and price cap."""
        if listing_type != "rent":
            # Rent.com.au only specializes in rentals
            return []

        listings: List[CanonicalListing] = []
        loc_slug = suburb_or_city.lower().replace(" ", "-") if suburb_or_city and suburb_or_city != "all" else "australia"
        price_param = f"?price_max={max_price}" if max_price and max_price > 0 else ""

        url = f"{self.BASE_URL}/properties/{loc_slug}{price_param}"
        resp = self.safe_get(url)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Parse JSON-LD metadata
        residences = {}
        events = {}
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(s.string)
                items = data if isinstance(data, list) else [data]
                for it in items:
                    t = it.get('@type')
                    u = it.get('url')
                    if t in ('SingleFamilyResidence', 'ApartmentComplex', 'Residence', 'Place', 'Apartment') and u:
                        residences[u] = it
                    elif t == 'Event':
                        loc = it.get('location', {})
                        lu = loc.get('url') if isinstance(loc, dict) else None
                        if lu:
                            events[lu] = it
            except Exception:
                continue

        # 2. Parse HTML listing cards and correlate with JSON-LD
        cards = soup.find_all('article') or soup.find_all('div', class_=lambda c: c and 'property' in c.lower())
        
        # Also process residences found directly from JSON-LD
        for u, res in residences.items():
            try:
                addr_data = res.get('address', {})
                street = addr_data.get('streetAddress', '')
                suburb = addr_data.get('addressLocality', '')
                st = addr_data.get('addressRegion', state.upper() if state != 'all' else 'NSW')
                postcode = addr_data.get('postalCode', '')

                # Geo coordinates
                geo = res.get('geo', {})
                lat = float(geo.get('latitude')) if geo.get('latitude') else None
                lng = float(geo.get('longitude')) if geo.get('longitude') else None

                address = PropertyAddress(
                    street=street,
                    suburb=suburb,
                    state=st,
                    postcode=postcode,
                    lat=lat,
                    lng=lng
                )

                # Price
                raw_price = ""
                offers = res.get('offers', {})
                if isinstance(offers, dict):
                    raw_price = str(offers.get('price', ''))
                price = parse_rental_price(raw_price)

                # Features
                beds = int(res.get('numberOfRooms', 1)) if res.get('numberOfRooms') else 1
                baths = int(res.get('numberOfBathroomsTotal', 1)) if res.get('numberOfBathroomsTotal') else 1
                cars = 1
                desc = res.get('description', '')
                image = res.get('image', '')
                if isinstance(image, list) and image:
                    image = image[0]

                features = detect_property_features(f"{beds} bed {baths} bath", desc)
                features.beds = beds
                features.baths = baths

                # Inspections
                inspections = []
                if u in events:
                    ev = events[u]
                    st_time = ev.get('startDate')
                    if st_time:
                        inspections.append(InspectionSlot(
                            start_time=st_time,
                            end_time=ev.get('endDate'),
                            raw_text=str(ev)
                        ))

                canonical_id = f"rent_{address.generate_canonical_key()}"
                portal_src = PortalSource(
                    portal=self.PORTAL_NAME,
                    url=u,
                    external_id=u.split('/')[-1]
                )

                listing = CanonicalListing(
                    id=canonical_id,
                    title=f"{street}, {suburb}",
                    address=address,
                    price=price,
                    features=features,
                    listing_type="rent",
                    description=desc[:500] if desc else "",
                    image_url=image or "",
                    inspections=inspections,
                    sources=[portal_src]
                )
                listings.append(listing)
            except Exception as e:
                logger.error(f"[{self.PORTAL_NAME}] Error parsing listing {u}: {e}")

        logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings for '{suburb_or_city}'.")
        return listings
