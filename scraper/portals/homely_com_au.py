"""
Homely.com.au Portal Scraper
Extracts rental & sale properties from Homely.com.au across Australia.
"""

import json
import logging
import re
from bs4 import BeautifulSoup
from typing import List, Optional
from ..base import BasePortalScraper
from ..models import CanonicalListing, PropertyAddress, PriceInfo, PropertyFeatures, PortalSource, InspectionSlot
from ..normalizer import parse_rental_price, parse_sale_price, detect_property_features, parse_australian_address

logger = logging.getLogger(__name__)

class HomelyComAuScraper(BasePortalScraper):
    PORTAL_NAME = "homely.com.au"
    BASE_URL = "https://www.homely.com.au"

    def scrape(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent"
    ) -> List[CanonicalListing]:
        """Scrapes listings from Homely.com.au."""
        listings: List[CanonicalListing] = []
        mode_path = "for-rent" if listing_type == "rent" else "for-sale"
        loc_slug = suburb_or_city.lower().replace(" ", "-") if suburb_or_city and suburb_or_city != "all" else "australia"
        
        url = f"{self.BASE_URL}/{mode_path}/{loc_slug}"
        params = {}
        if max_price and max_price > 0:
            params["price"] = f"0-{max_price}"

        resp = self.safe_get(url, params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Check for JSON state embedded in script tags
        state_tag = soup.find('script', id='__NEXT_DATA__') or soup.find('script', text=re.compile(r'window\.__INITIAL_STATE__'))
        if state_tag and state_tag.string:
            try:
                # If Next.js data is found
                if '__NEXT_DATA__' in str(state_tag):
                    data = json.loads(state_tag.string)
                    items = data.get('props', {}).get('pageProps', {}).get('listings', [])
                    for it in items:
                        parsed = self._parse_homely_json_item(it, listing_type)
                        if parsed:
                            listings.append(parsed)
                    if listings:
                        logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings via JSON state.")
                        return listings
            except Exception as e:
                logger.warning(f"[{self.PORTAL_NAME}] Error parsing Homely JSON state: {e}")

        # HTML parsing fallback
        cards = soup.find_all('article') or soup.find_all('div', class_=lambda c: c and 'ListingCard' in c)
        for card in cards:
            try:
                link = card.find('a', href=re.compile(r'/properties/'))
                if not link:
                    continue
                href = link['href']
                full_url = href if href.startswith('http') else self.BASE_URL + href

                text = card.get_text(' | ', strip=True)
                price_info = parse_rental_price(text) if listing_type == "rent" else parse_sale_price(text)
                
                addr_match = re.search(r'([0-9A-Za-z\s\/\,\-]+(?:NSW|VIC|QLD|WA|SA|ACT|TAS)\s*[0-9]{4})', text)
                addr_str = addr_match.group(1) if addr_match else text.split('|')[0]
                address = parse_australian_address(addr_str, default_state=state.upper() if state != 'all' else 'NSW')

                img = card.find('img')
                img_url = img.get('src') if img else ""

                features = detect_property_features(text)
                portal_src = PortalSource(
                    portal=self.PORTAL_NAME,
                    url=full_url,
                    external_id=str(abs(hash(full_url)))
                )

                listing = CanonicalListing(
                    id=f"homely_{address.generate_canonical_key()}",
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

    def _parse_homely_json_item(self, it: dict, listing_type: str) -> Optional[CanonicalListing]:
        try:
            addr = it.get('address', {})
            address = PropertyAddress(
                street=addr.get('streetAddress', ''),
                suburb=addr.get('suburb', ''),
                state=addr.get('state', 'NSW'),
                postcode=str(addr.get('postcode', '')),
                lat=it.get('latitude'),
                lng=it.get('longitude')
            )
            raw_price = it.get('price', '') or it.get('displayPrice', '')
            price = parse_rental_price(raw_price) if listing_type == "rent" else parse_sale_price(raw_price)

            features = PropertyFeatures(
                beds=it.get('bedrooms', 1),
                baths=it.get('bathrooms', 1),
                cars=it.get('carspaces', 1),
                prop_type=it.get('propertyType', 'House')
            )

            url = f"{self.BASE_URL}{it.get('url', '')}"
            img = it.get('mainImage', {}).get('url', '')

            portal_src = PortalSource(portal=self.PORTAL_NAME, url=url, external_id=str(it.get('id', '')))

            return CanonicalListing(
                id=f"homely_{address.generate_canonical_key()}",
                title=f"{address.street}, {address.suburb}",
                address=address,
                price=price,
                features=features,
                listing_type=listing_type,
                image_url=img,
                sources=[portal_src]
            )
        except Exception:
            return None
