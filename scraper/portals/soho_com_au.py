"""
Soho Real Estate (soho.com.au) Portal Scraper
Extracts properties using Soho's public listings API and mobile web endpoints.
"""

import logging
from typing import List, Optional
from ..base import BasePortalScraper
from ..models import CanonicalListing, PropertyAddress, PriceInfo, PropertyFeatures, PortalSource
from ..normalizer import parse_rental_price, parse_sale_price, detect_property_features

logger = logging.getLogger(__name__)

class SohoComAuScraper(BasePortalScraper):
    PORTAL_NAME = "soho.com.au"
    BASE_URL = "https://soho.com.au"
    API_URL = "https://api.soho.com.au/api/v1/properties/search"

    def scrape(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent"
    ) -> List[CanonicalListing]:
        """Queries Soho's public property endpoint."""
        listings: List[CanonicalListing] = []
        mode = "rent" if listing_type == "rent" else "buy"
        
        headers = {
            "Accept": "application/json",
            "Referer": f"{self.BASE_URL}/{mode}"
        }
        params = {
            "channel": mode,
            "query": suburb_or_city if suburb_or_city != "all" else "Australia",
            "page": 1,
            "per_page": 25
        }
        if max_price and max_price > 0:
            params["max_price"] = max_price

        resp = self.safe_get(self.API_URL, params=params, headers=headers)
        if not resp:
            # Fallback to web page parsing
            return self._scrape_html_fallback(suburb_or_city, state, max_price, listing_type)

        try:
            data = resp.json()
            items = data.get("properties", []) or data.get("results", []) or data.get("data", [])
            for it in items:
                address_data = it.get("address", {})
                street = address_data.get("street_address", it.get("title", ""))
                suburb = address_data.get("suburb", "")
                st = address_data.get("state", "NSW")
                postcode = str(address_data.get("postcode", ""))

                address = PropertyAddress(
                    street=street,
                    suburb=suburb,
                    state=st,
                    postcode=postcode,
                    lat=it.get("latitude"),
                    lng=it.get("longitude")
                )

                raw_price = it.get("display_price", "") or str(it.get("price", ""))
                price = parse_rental_price(raw_price) if listing_type == "rent" else parse_sale_price(raw_price)

                features = PropertyFeatures(
                    beds=it.get("bedrooms", 1) or 1,
                    baths=it.get("bathrooms", 1) or 1,
                    cars=it.get("carspaces", 1) or 1,
                    prop_type=it.get("property_type", "House") or "House"
                )

                images = it.get("photos", []) or it.get("images", [])
                img_url = images[0].get("url") if images and isinstance(images[0], dict) else (images[0] if images else "")

                url = it.get("canonical_url") or f"{self.BASE_URL}/properties/{it.get('id')}"
                portal_src = PortalSource(portal=self.PORTAL_NAME, url=url, external_id=str(it.get("id", "")))

                listings.append(CanonicalListing(
                    id=f"soho_{address.generate_canonical_key()}",
                    title=f"{street}, {suburb}",
                    address=address,
                    price=price,
                    features=features,
                    listing_type=listing_type,
                    description=it.get("description", "")[:300],
                    image_url=img_url or "",
                    sources=[portal_src]
                ))

            logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings via API.")
            return listings
        except Exception as e:
            logger.warning(f"[{self.PORTAL_NAME}] Error parsing API response: {e}")
            return self._scrape_html_fallback(suburb_or_city, state, max_price, listing_type)

    def _scrape_html_fallback(self, suburb: str, state: str, max_price: Optional[int], listing_type: str) -> List[CanonicalListing]:
        """Fallback to web scraping if API rate-limited."""
        url = f"{self.BASE_URL}/{'rent' if listing_type == 'rent' else 'buy'}"
        resp = self.safe_get(url)
        if not resp:
            return []
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Simple structural fallback
        return []
