import requests
import json
import re
import urllib.parse
import logging
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-AU,en;q=0.9'
}

SUBURB_FALLBACK_COORDS = {
    "nowra": (-34.8727, 150.6019),
    "bomaderry": (-34.8483, 150.6186),
    "north nowra": (-34.8582, 150.5891),
    "south nowra": (-34.9080, 150.6120),
    "west nowra": (-34.8910, 150.5880),
    "worrigee": (-34.8930, 150.6380),
    "bangalee": (-34.8380, 150.5780),
    "terara": (-34.8780, 150.6550),
    "mundamia": (-34.8850, 150.5480),
}

def extract_price(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r'\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)', text)
    if m:
        try:
            val = int(m.group(1).replace(',', ''))
            return val if val >= 100 else None
        except ValueError:
            return None
    return None

def clean_suburb(suburb_raw: str) -> str:
    if not suburb_raw:
        return "Nowra"
    s = suburb_raw.strip().title()
    for known in ["North Nowra", "South Nowra", "West Nowra", "Bomaderry", "Bangalee", "Worrigee", "Terara", "Mundamia", "Nowra"]:
        if known.lower() in s.lower():
            return known
    return s

def detect_pets_allowed(text: str = "", desc: str = "", has_pet_tag: bool = False, prop_type: str = "House") -> int:
    if has_pet_tag:
        return 1
    combined = f"{text} {desc}".lower()
    if re.search(r'\b(no pets?|strictly no pets?|not suitable for pets?|pets? not permitted|pets? not allowed|sorry,? no pets?)\b', combined):
        return 0
    if re.search(r'\b(pets?\s*(?:considered|allowed|welcome|friendly|ok|permitted|negotiable|approved|upon application|on application))\b', combined):
        return 1
    if re.search(r'\b(dog|cat|pets?)\s*(?:friendly|allowed|welcome|ok)\b', combined):
        return 1
    return 0

def scrape_rentals(suburb_or_postcode: str = "australia", max_price: int = 550) -> List[Dict[str, Any]]:
    """
    Scrapes rental listings from Rent.com.au.
    Returns list of parsed listing dictionaries.
    """
    listings = []
    seen_urls = set()
    
    # Query up to max_price + 25 to catch edge cases
    query_price = max(max_price + 25, 550)
    target = suburb_or_postcode.lower().strip()
    
    pages = [
        f"https://www.rent.com.au/properties/{target}?price_max={query_price}"
    ]
    
    for url in pages:
        try:
            logger.info(f"Fetching {url}")
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch {url}, status: {resp.status_code}")
                continue
            soup = BeautifulSoup(resp.text, 'html.parser')
        except Exception as e:
            logger.error(f"Error requesting {url}: {e}")
            continue
            
        residences = {}
        events = {}
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                d = json.loads(s.string)
                items = d if isinstance(d, list) else [d]
                for it in items:
                    t = it.get('@type')
                    u = it.get('url')
                    if t == 'Residence' and u:
                        residences[u] = it
                    elif t == 'Event' and u:
                        events[u] = it
            except Exception:
                pass
                
        for art in soup.find_all('article'):
            link = art.find('a', href=True)
            if not link:
                continue
            href = link['href']
            full_url = href if href.startswith('http') else 'https://www.rent.com.au' + href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            res = residences.get(full_url, {})
            ev = events.get(full_url, {})
            text = art.get_text(' ', strip=True)
            raw_desc = res.get('description', '')
            
            # Price extraction with comma support
            price = extract_price(raw_desc) or extract_price(text)
                
            # Bedrooms, bathrooms, car spaces
            beds = None
            baths = None
            cars = None
            
            bm = re.search(r'(\d+)\s*bed', text, re.I) or re.search(r'(\d+)\s*bed', raw_desc, re.I)
            if bm:
                beds = int(bm.group(1))
                
            bam = re.search(r'(\d+)\s*bath', text, re.I) or re.search(r'(\d+)\s*bath', raw_desc, re.I)
            if bam:
                baths = int(bam.group(1))
                
            cm = re.search(r'(\d+)\s*(?:car spaces|car|parking|garage)', text, re.I)
            if cm:
                cars = int(cm.group(1))
            else:
                cars = 1 if ('garage' in text.lower() or 'carport' in text.lower() or 'parking' in text.lower()) else 0
                
            # Address & Suburb & Postcode
            addr_obj = res.get('address', [{}])[0] if res.get('address') else {}
            raw_street = addr_obj.get('streetAddress') or link.get_text(strip=True)
            raw_suburb = addr_obj.get('addressLocality', '')
            postcode = addr_obj.get('postalCode')
            
            if not postcode:
                pm = re.search(r'\b(254[01])\b', text) or re.search(r'\b(254[01])\b', full_url)
                postcode = pm.group(1) if pm else '2541'
                
            suburb = clean_suburb(raw_suburb)
            street = raw_street.strip() if raw_street else f"Property in {suburb}"
            
            # High-res Image
            img = art.find('img')
            img_url = None
            if img:
                src = img.get('src') or img.get('data-src') or ''
                if '_next/image?url=' in src:
                    q = urllib.parse.parse_qs(urllib.parse.urlparse(src).query)
                    img_url = q.get('url', [None])[0]
                elif src.startswith('http'):
                    img_url = src
            if not img_url:
                img_url = ev.get('image')
                
            # Coordinates
            geo = res.get('geo', [{}])[0] if res.get('geo') else {}
            lat = geo.get('latitude')
            lng = geo.get('longitude')
            
            if not lat or not lng:
                fallback = SUBURB_FALLBACK_COORDS.get(suburb.lower(), (-34.8727, 150.6019))
                # Add slight jitter so multiple properties don't stack exactly on the same pixel
                import random
                lat = fallback[0] + random.uniform(-0.005, 0.005)
                lng = fallback[1] + random.uniform(-0.005, 0.005)
                
            # Property type
            prop_type = 'House'
            for pt in ['Townhouse', 'Villa', 'Duplex', 'Studio', 'Apartment', 'Unit', 'House']:
                if pt.lower() in text.lower() or pt.lower() in raw_desc.lower():
                    prop_type = pt
                    break
                    
            # Inspection time
            inspection = ev.get('startDate')
            
            # Title
            title = res.get('name') or f"{beds or ''} Bed {prop_type} in {suburb}".strip()
            
            # Pets allowed detection
            has_pet_tag = bool(art.find(attrs={'data-testid': 'feature-pets-allowed'}) or art.find('img', alt=lambda x: x and 'pet' in x.lower()))
            pets_allowed = detect_pets_allowed(text, raw_desc, has_pet_tag, prop_type)

            # Extract Listing ID
            lid_match = re.search(r'-(\d+)$', full_url)
            lid = lid_match.group(1) if lid_match else str(abs(hash(full_url)))
            
            listings.append({
                'id': lid,
                'url': full_url,
                'title': title,
                'street': street,
                'suburb': suburb,
                'postcode': '2541',
                'price': price,
                'beds': beds or 1,
                'baths': baths or 1,
                'cars': cars,
                'prop_type': prop_type,
                'image': img_url,
                'lat': lat,
                'lng': lng,
                'inspection': inspection,
                'desc': raw_desc or text[:250],
                'pets_allowed': pets_allowed,
                'source': 'rent.com.au'
            })
            
    return listings

def scrape_raywhite_shoalhaven(max_price: int = 550) -> List[Dict[str, Any]]:
    """Scrapes local listings from Ray White Shoalhaven Central Group."""
    url = "https://raywhiteshoalhavencentralgroup.com.au/properties/residential-for-rent"
    results = []
    try:
        logger.info(f"Fetching Ray White Shoalhaven: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        for it in soup.find_all('div', class_='proplist_item'):
            text = it.get_text(' | ', strip=True)
            link_el = it.find('a', href=re.compile(r'/properties/residential-for-rent/'))
            if not link_el:
                continue
            href = link_el['href']
            full_url = href if href.startswith('http') else 'https://raywhiteshoalhavencentralgroup.com.au' + href
            
            # Check if regional NSW suburb
            suburb = None
            for s in ["North Nowra", "South Nowra", "West Nowra", "Bomaderry", "Bangalee", "Worrigee", "Nowra"]:
                if s.lower() in text.lower() or s.lower().replace(' ', '-') in full_url.lower():
                    suburb = s
                    break
            if not suburb:
                continue
                
            price = extract_price(text)
            
            # beds, baths, cars
            beds = 1
            baths = 1
            cars = 1
            bm = re.search(r'(\d+)\s*\|\s*Beds', text, re.I)
            if bm: beds = int(bm.group(1))
            bam = re.search(r'(\d+)\s*\|\s*Baths', text, re.I)
            if bam: baths = int(bam.group(1))
            cm = re.search(r'(\d+)\s*\|\s*Car', text, re.I)
            if cm: cars = int(cm.group(1))
            
            # Address
            addr_m = re.search(r'(?:Weekly|Now|Friday|Thursday|Monday|Tuesday|Wednesday|Saturday|Sunday)\s*\|\s*([0-9A-Za-z\s\/]+,\s*[A-Za-z\s]+)', text)
            street = addr_m.group(1).split(',')[0].strip() if addr_m else f"Property in {suburb}"
            
            # Image
            img = it.find('img')
            img_url = img.get('src') if img else None
            
            # Fallback coords
            fallback = SUBURB_FALLBACK_COORDS.get(suburb.lower(), (-34.8727, 150.6019))
            import random
            lat = fallback[0] + random.uniform(-0.005, 0.005)
            lng = fallback[1] + random.uniform(-0.005, 0.005)
            
            # Prop type
            prop_type = 'House'
            for pt in ['Duplex', 'Townhouse', 'Villa', 'Unit', 'Apartment', 'House']:
                if pt.lower() in text.lower():
                    prop_type = pt
                    break
                    
            lid_m = re.search(r'/(\d+)$', full_url)
            lid = "rw_" + (lid_m.group(1) if lid_m else str(abs(hash(full_url))))
            pets_allowed = detect_pets_allowed(text, '', ('pet' in text.lower() or prop_type == 'House'), prop_type)
            
            results.append({
                'id': lid,
                'url': full_url,
                'title': f"{street}, {suburb}",
                'street': street,
                'suburb': suburb,
                'postcode': '2541',
                'price': price,
                'beds': beds,
                'baths': baths,
                'cars': cars,
                'prop_type': prop_type,
                'image': img_url,
                'lat': lat,
                'lng': lng,
                'inspection': None,
                'desc': text[:250],
                'pets_allowed': pets_allowed,
                'source': 'Ray White Nowra'
            })
    except Exception as e:
        logger.error(f"Error scraping Ray White: {e}")
    return results

scrape_2541_rentals = scrape_rentals

def send_webhook_alert(webhook_url: str, new_listings: List[Dict[str, Any]]):
    """Sends notification to Discord or custom webhook if new listings are found."""
    if not webhook_url or not new_listings:
        return
    try:
        content_lines = [f"🚨 **{len(new_listings)} New Rental(s) Found!**\n"]
        for item in new_listings[:5]:
            insp_text = f" | 📅 Inspection: {item.get('inspection')[:16]}" if item.get('inspection') else ""
            content_lines.append(
                f"• **${item.get('price')}/wk** - {item.get('street')}, {item.get('suburb')} "
                f"({item.get('beds')} bed, {item.get('baths')} bath, {item.get('prop_type')}){insp_text}\n<{item.get('url')}>"
            )
        payload = {"content": "\n".join(content_lines)}
        requests.post(webhook_url, json=payload, timeout=8)
        logger.info("Webhook notification sent successfully.")
    except Exception as e:
        logger.warning(f"Failed to send webhook notification: {e}")

def run_scraper_and_sync(suburb_or_city: str = "australia", max_price: Optional[int] = None) -> Dict[str, Any]:
    """Runs the multi-portal scraper across Australian portals and syncs to database."""
    from scraper.engine import AustralianRentalScraperEngine
    database.init_db()
    settings = database.get_settings()
    configured_max = int(settings.get("max_price", 550))
    effective_max = max_price if max_price is not None else configured_max
    webhook_url = settings.get("webhook_url", "")

    engine = AustralianRentalScraperEngine()
    canonical_listings = engine.crawl(
        suburb_or_city=suburb_or_city,
        max_price=effective_max,
        listing_type="rent"
    )

    # Direct local agency fallback
    items_rw = scrape_raywhite_shoalhaven(max_price=effective_max)
    for rw in items_rw:
        database.upsert_listing(rw)

    result = engine.sync_to_database(canonical_listings, webhook_url=webhook_url)
    return {
        "total_scraped": result.get("total_canonical", len(canonical_listings)) + len(items_rw),
        "newly_added": result.get("new_added", 0),
        "updated": result.get("existing_updated", 0),
        "price_drops": result.get("price_drops", 0)
    }

if __name__ == "__main__":
    result = run_scraper_and_sync()
    print("Multi-portal sync complete:", result)
