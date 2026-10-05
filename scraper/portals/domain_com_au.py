"""
Domain.com.au Portal Scraper
Extracts rental & sale properties from Australia's #2 real estate network via Next.js SSR JSON payloads.
"""

import json
import logging
import re
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from ..base import BasePortalScraper
from ..models import CanonicalListing, PropertyAddress, PriceInfo, PropertyFeatures, PortalSource, InspectionSlot
from ..normalizer import parse_rental_price, parse_sale_price, detect_property_features, parse_inspection_datetime, parse_australian_address

logger = logging.getLogger(__name__)

class DomainComAuScraper(BasePortalScraper):
    PORTAL_NAME = "domain.com.au"
    BASE_URL = "https://www.domain.com.au"

    def scrape(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent"
    ) -> List[CanonicalListing]:
        """
        Scrapes listings from Domain.com.au using Next.js __NEXT_DATA__ payload
        with fallback to HTML card extraction.
        """
        listings: List[CanonicalListing] = []
        mode_path = "rent" if listing_type == "rent" else "sale"
        
        # Build query parameters
        params: Dict[str, Any] = {
            "search": suburb_or_city if suburb_or_city and suburb_or_city != "all" else "australia",
            "sort": "dateupdated-desc"
        }
        if max_price and max_price > 0:
            params["price"] = f"0-{max_price}"

        url = f"{self.BASE_URL}/{mode_path}/"
        resp = self.safe_get(url, params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Strategy 1: Extract __NEXT_DATA__ JSON payload (fastest & most accurate)
        next_data_tag = soup.find('script', id='__NEXT_DATA__')
        if next_data_tag and next_data_tag.string:
            try:
                data = json.loads(next_data_tag.string)
                props = data.get('props', {}).get('pageProps', {})
                component_props = props.get('componentProps', {})
                
                # Check for listingsMap or searchResults
                listings_map = component_props.get('listingsMap', {})
                if not listings_map:
                    # Alternative structure in some Next.js revisions
                    listings_map = props.get('listingsMap', {}) or component_props.get('searchResults', {})

                if isinstance(listings_map, dict):
                    for listing_id, item in listings_map.items():
                        parsed = self._parse_domain_json_item(item, listing_type)
                        if parsed:
                            listings.append(parsed)

                if listings:
                    logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings via __NEXT_DATA__.")
                    return listings
            except Exception as e:
                logger.warning(f"[{self.PORTAL_NAME}] Error parsing __NEXT_DATA__: {e}")

        # Strategy 2: Fallback to HTML Card Extraction
        cards = soup.find_all('li', class_=lambda c: c and 'listing' in c.lower()) or soup.find_all('div', class_=lambda c: c and 'css-' in c.lower() and 'property' in c.lower())
        for card in cards:
            try:
                link = card.find('a', href=re.compile(r'/\d+$'))
                if not link:
                    continue
                href = link['href']
                full_url = href if href.startswith('http') else self.BASE_URL + href

                # Address
                addr_text = ""
                addr_el = card.find('span', {'data-testid': 'address-line1'}) or card.find('h2')
                if addr_el:
                    addr_text = addr_el.get_text(' ', strip=True)

                # Price
                price_text = ""
                price_el = card.find('p', {'data-testid': 'listing-card-price'}) or card.find('div', class_=lambda c: c and 'price' in c.lower())
                if price_el:
                    price_text = price_el.get_text(strip=True)

                price_info = parse_sale_price(price_text) if listing_type == "sale" else parse_rental_price(price_text)
                address = parse_australian_address(addr_text, default_state=state.upper() if state != 'all' else 'NSW')
                features = detect_property_features(card.get_text(' ', strip=True))

                img_el = card.find('img')
                img_url = img_el.get('src') if img_el else ""

                lid = f"domain_{address.generate_canonical_key()}"
                portal_src = PortalSource(
                    portal=self.PORTAL_NAME,
                    url=full_url,
                    external_id=str(abs(hash(full_url)))
                )

                listing = CanonicalListing(
                    id=lid,
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
                logger.error(f"[{self.PORTAL_NAME}] Error parsing HTML card: {e}")

        logger.info(f"[{self.PORTAL_NAME}] Extracted {len(listings)} listings via HTML fallback.")
        return listings

    def _parse_domain_json_item(self, item: Dict[str, Any], listing_type: str) -> Optional[CanonicalListing]:
        """Parses a Domain listing item from the __NEXT_DATA__ dictionary."""
        try:
            listing_model = item.get('listingModel', item)
            addr_data = listing_model.get('address', {})
            
            street = addr_data.get('street', '')
            suburb = addr_data.get('suburb', '')
            st = addr_data.get('state', 'NSW')
            postcode = str(addr_data.get('postcode', ''))

            geo = addr_data.get('latLng', {})
            lat = float(geo.get('lat')) if geo.get('lat') else None
            lng = float(geo.get('lng')) if geo.get('lng') else None

            address = PropertyAddress(
                street=street,
                suburb=suburb,
                state=st,
                postcode=postcode,
                lat=lat,
                lng=lng
            )

            # Price
            raw_price = listing_model.get('price', '') or listing_model.get('priceDetails', {}).get('price', '')
            price_info = parse_sale_price(raw_price) if listing_type == "sale" else parse_rental_price(raw_price)

            # Features
            features_data = listing_model.get('features', {})
            beds = int(features_data.get('beds', 1)) if features_data.get('beds') else 1
            baths = int(features_data.get('baths', 1)) if features_data.get('baths') else 1
            cars = int(features_data.get('parking', 1)) if features_data.get('parking') else 1
            prop_type = listing_model.get('propertyType', 'House')

            desc = listing_model.get('description', '')
            features = detect_property_features(f"{beds} bed {baths} bath {prop_type}", desc, explicit_type=prop_type)
            features.beds = beds
            features.baths = baths
            features.cars = cars

            # Images
            media = listing_model.get('media', [])
            images = [m.get('url') for m in media if m.get('category') == 'image' and m.get('url')]
            primary_img = images[0] if images else ""

            # URL
            url_path = listing_model.get('url', '')
            full_url = f"{self.BASE_URL}{url_path}" if url_path.startswith('/') else url_path

            # Inspections
            inspections = []
            insp_list = listing_model.get('inspectionTimes', [])
            for insp in insp_list:
                opening = insp.get('openingTime')
                if opening:
                    inspections.append(InspectionSlot(
                        start_time=opening,
                        end_time=insp.get('closingTime'),
                        raw_text=str(insp)
                    ))

            canonical_id = f"domain_{address.generate_canonical_key()}"
            portal_src = PortalSource(
                portal=self.PORTAL_NAME,
                url=full_url,
                external_id=str(listing_model.get('id', ''))
            )

            return CanonicalListing(
                id=canonical_id,
                title=f"{street}, {suburb}",
                address=address,
                price=price_info,
                features=features,
                listing_type=listing_type,
                description=desc[:500] if desc else "",
                image_url=primary_img,
                extra_images=images[1:5],
                inspections=inspections,
                sources=[portal_src]
            )
        except Exception as e:
            logger.error(f"[{self.PORTAL_NAME}] Error normalizing JSON item: {e}")
            return None
