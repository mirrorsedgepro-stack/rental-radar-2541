"""
Allhomes.com.au Portal Scraper
Extracts properties from Allhomes, dominant across the ACT, Canberra, and regional NSW.
"""

import logging
import re
from bs4 import BeautifulSoup
from typing import List, Optional
from ..base import BasePortalScraper
from ..models import CanonicalListing, PropertyAddress, PriceInfo, PropertyFeatures, PortalSource
from ..normalizer import parse_rental_price, parse_sale_price, detect_property_features, parse_australian_address

logger = logging.getLogger(__name__)

class AllhomesComAuScraper(BasePortalScraper):
    PORTAL_NAME = "allhomes.com.au"
    BASE_URL = "https://www.allhomes.com.au"

    def scrape(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent"
    ) -> List[CanonicalListing]:
        """Scrapes listings from Allhomes.com.au."""
        listings: List[CanonicalListing] = []
        mode = "rent" if listing_type == "rent" else "sale"
        loc_str = suburb_or_city.lower().replace(" ", "-") if suburb_or_city and suburb_or_city != "all" else "canberra-act"
        
        url = f"{self.BASE_URL}/{mode}/{loc_str}/"
        params = {}
        if max_price and max_price > 0:
            params["price"] = f"0-{max_price}"

        resp = self.safe_get(url, params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.find_all('div', class_=lambda c: c and 'ListingCard' in c) or soup.find_all('div', class_=lambda c: c and 'listing' in c.lower())

        for card in cards:
            try:
                link = card.find('a', href=re.compile(r'/ah/'))
                if not link:
                    continue
                href = link['href']
                full_url = href if href.startswith('http') else self.BASE_URL + href

                text = card.get_text(' | ', strip=True)
                price_info = parse_rental_price(text) if listing_type == "rent" else parse_sale_price(text)
                address = parse_australian_address(text.split('|')[0], default_state="ACT")
                features = detect_property_features(text)

                img = card.find('img')
                img_url = img.get('src') if img else ""

                portal_src = PortalSource(
                    portal=self.PORTAL_NAME,
                    url=full_url,
                    external_id=str(abs(hash(full_url)))
                )

                listing = CanonicalListing(
                    id=f"allhomes_{address.generate_canonical_key()}",
                    title=f"{address.street}, {address.suburb}",
                    address=address,
                    price=price_info,
                    features=features,
                    listing_type=listing_type,
                    description=text[:250],
                    image_url=img_url or "",
                    sources=[portal_src]
                )
                listings.append(listing)
            except Exception as e:
                logger.error(f"[{self.PORTAL_NAME}] Error parsing card: {e}")

        logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings.")
        return listings
