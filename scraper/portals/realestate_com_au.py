"""
Realestate.com.au Portal Scraper
Extracts properties from Australia's #1 portal with anti-bot resilience,
mobile emulation, and structured Next.js/OpenGraph fallback parsing.
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

class RealestateComAuScraper(BasePortalScraper):
    PORTAL_NAME = "realestate.com.au"
    BASE_URL = "https://www.realestate.com.au"

    def scrape(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent"
    ) -> List[CanonicalListing]:
        """
        Scrapes listings from Realestate.com.au.
        Constructs search URL formatted to REA search structure:
        e.g., https://www.realestate.com.au/rent/in-sydney/list-1?activeSort=list-date
        """
        listings: List[CanonicalListing] = []
        mode = "rent" if listing_type == "rent" else "buy"
        loc_str = suburb_or_city.lower().replace(" ", "-") if suburb_or_city and suburb_or_city != "all" else "australia"
        
        # Price query formatting for REA
        price_clause = f"-with-maxPrice-{max_price}" if max_price and max_price > 0 else ""
        url = f"{self.BASE_URL}/{mode}{price_clause}-in-{loc_str}/list-1?activeSort=list-date"

        # Additional anti-detection headers
        custom_headers = {
            "Host": "www.realestate.com.au",
            "Referer": "https://www.google.com.au/",
            "Sec-Ch-Ua": '"Chromium";v="129", "Not=A?Brand";v="24", "Google Chrome";v="129"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }

        resp = self.safe_get(url, headers=custom_headers)
        if not resp:
            logger.info(f"[{self.PORTAL_NAME}] Standard search blocked or unavailable. Falling back to alternative portals.")
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 1. Strategy: Extract Argus / Next.js JSON state
        scripts = soup.find_all('script')
        for s in scripts:
            if s.string and 'window.argus' in s.string or 'props' in (s.string or ''):
                try:
                    match = re.search(r'window\.argus\s*=\s*({.*?});', s.string, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        # Parse Argus search results if found
                        results = data.get('searchResults', {}).get('tier1', [])
                        for item in results:
                            parsed = self._parse_rea_json(item, listing_type)
                            if parsed:
                                listings.append(parsed)
                        if listings:
                            logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings via Argus data.")
                            return listings
                except Exception:
                    continue

        # 2. Strategy: Parse HTML Listing Cards (tiered-results)
        cards = soup.find_all('article', class_=lambda c: c and 'result-card' in c) or soup.find_all('div', class_=lambda c: c and 'residential-card' in c)
        for card in cards:
            try:
                link = card.find('a', href=re.compile(r'/property-'))
                if not link:
                    continue
                href = link['href']
                full_url = href if href.startswith('http') else self.BASE_URL + href

                # Address
                addr_el = card.find('a', class_=lambda c: c and 'details-link' in c) or card.find('h2')
                addr_text = addr_el.get_text(' ', strip=True) if addr_el else ""

                # Price
                price_el = card.find('span', class_=lambda c: c and 'property-price' in c)
                price_text = price_el.get_text(strip=True) if price_el else ""

                price_info = parse_sale_price(price_text) if listing_type == "sale" else parse_rental_price(price_text)
                address = parse_australian_address(addr_text, default_state=state.upper() if state != 'all' else 'NSW')
                features = detect_property_features(card.get_text(' ', strip=True))

                img_el = card.find('img')
                img_url = img_el.get('src') if img_el else ""

                portal_src = PortalSource(
                    portal=self.PORTAL_NAME,
                    url=full_url,
                    external_id=str(abs(hash(full_url)))
                )

                listing = CanonicalListing(
                    id=f"rea_{address.generate_canonical_key()}",
                    title=f"{address.street}, {address.suburb}",
                    address=address,
                    price=price_info,
                    features=features,
                    listing_type=listing_type,
                    description=card.get_text(' | ', strip=True)[:300],
                    image_url=img_url or "",
                    sources=[portal_src]
                )
                listings.append(listing)
            except Exception as e:
                logger.error(f"[{self.PORTAL_NAME}] Error parsing card: {e}")

        logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings.")
        return listings

    def _parse_rea_json(self, item: dict, listing_type: str) -> Optional[CanonicalListing]:
        """Parses internal REA search item representation."""
        try:
            addr = item.get('address', {})
            address = PropertyAddress(
                street=addr.get('street', ''),
                suburb=addr.get('suburb', ''),
                state=addr.get('state', 'NSW'),
                postcode=str(addr.get('postcode', '')),
                lat=item.get('location', {}).get('latitude'),
                lng=item.get('location', {}).get('longitude')
            )
            raw_price = item.get('price', {}).get('display', '')
            price = parse_rental_price(raw_price) if listing_type == "rent" else parse_sale_price(raw_price)

            features = PropertyFeatures(
                beds=item.get('features', {}).get('bedrooms', 1),
                baths=item.get('features', {}).get('bathrooms', 1),
                cars=item.get('features', {}).get('carspaces', 1),
                prop_type=item.get('propertyType', 'House')
            )

            url = f"{self.BASE_URL}{item.get('prettyUrl', '')}"
            img = item.get('images', [{}])[0].get('url', '')

            portal_src = PortalSource(portal=self.PORTAL_NAME, url=url, external_id=str(item.get('id', '')))

            return CanonicalListing(
                id=f"rea_{address.generate_canonical_key()}",
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
