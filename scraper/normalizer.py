"""
Data Normalization & Cleaning Utilities for Australian Real Estate
Standardizes addresses, prices (pw/pcm), inspection dates, and property features.
"""

import re
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime, timedelta
from .models import PropertyAddress, PriceInfo, PropertyFeatures

# Australian States & Territories
AU_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "ACT", "TAS", "NT"}

# Capital & major regional hub fallback coordinates
CITY_COORDINATES = {
    "sydney": (-33.8688, 151.2093),
    "melbourne": (-37.8136, 144.9631),
    "brisbane": (-27.4698, 153.0251),
    "perth": (-31.9505, 115.8605),
    "adelaide": (-34.9285, 138.6007),
    "hobart": (-42.8821, 147.3272),
    "canberra": (-35.2809, 149.1300),
    "darwin": (-12.4634, 130.8456),
    "gold coast": (-28.0167, 153.4000),
    "newcastle": (-32.9283, 151.7817),
    "wollongong": (-34.4278, 150.8931),
    "geelong": (-38.1499, 144.3617),
    "nowra": (-34.8727, 150.6019),
    "bomaderry": (-34.8483, 150.6186),
}

def parse_australian_address(raw_text: str, default_state: str = "NSW") -> PropertyAddress:
    """
    Parses unformatted Australian property address strings into structured PropertyAddress.
    Handles unit prefixes, street names, suburbs, state abbreviations, and 4-digit postcodes.
    Example: 'Unit 4/12-14 Ocean Street, Manly NSW 2095'
    """
    if not raw_text:
        return PropertyAddress(street="", suburb="", state=default_state, postcode="")

    text = raw_text.strip()
    
    # 1. Extract Postcode (4 digits at the end or near the end)
    postcode = ""
    postcode_match = re.search(r'\b(0[89]\d{2}|[1-9]\d{3})\b', text)
    if postcode_match:
        postcode = postcode_match.group(1)
        # Remove postcode from working text
        text = text[:postcode_match.start()] + text[postcode_match.end():]

    # 2. Extract State
    state = default_state
    for st in AU_STATES:
        state_match = re.search(rf'\b{st}\b', text, re.IGNORECASE)
        if state_match:
            state = st
            text = text[:state_match.start()] + text[state_match.end():]
            break

    # 3. Clean remaining text and split by commas
    parts = [p.strip() for p in text.split(',') if p.strip()]
    
    unit = None
    street = ""
    suburb = ""

    if len(parts) >= 2:
        street = parts[0]
        suburb = parts[1].strip()
    elif len(parts) == 1:
        # Single string e.g. "14 George St Sydney"
        tokens = parts[0].split()
        if len(tokens) >= 3:
            suburb = tokens[-1]
            street = " ".join(tokens[:-1])
        else:
            street = parts[0]
            suburb = "Metro"

    # Extract unit number if formatted like '4/12' or 'Unit 4/12'
    unit_match = re.search(r'^(?:unit|apt|suite|flat)?\s*([0-9A-Za-z]+)\s*[\/\-]\s*(.+)$', street, re.IGNORECASE)
    if unit_match:
        unit = unit_match.group(1)
        street = unit_match.group(2)

    # Lookup lat/lng fallback if suburb known
    lat, lng = None, None
    suburb_lower = suburb.lower().strip()
    if suburb_lower in CITY_COORDINATES:
        lat, lng = CITY_COORDINATES[suburb_lower]

    return PropertyAddress(
        street=street.strip(),
        suburb=suburb.title().strip(),
        state=state.upper(),
        postcode=postcode,
        unit=unit,
        lat=lat,
        lng=lng
    )

def parse_rental_price(text: str) -> PriceInfo:
    """
    Parses messy rental price strings into normalized weekly and monthly amounts.
    Handles: '$550 pw', '$550 per week', '$2,400 pcm', '$600 - $650', 'Deposit Taken'.
    """
    if not text:
        return PriceInfo(raw_text="")

    raw = text.strip()
    lower = raw.lower()

    if "deposit taken" in lower or "leased" in lower or "application approved" in lower:
        return PriceInfo(raw_text=raw, is_deposit_taken=True)

    if "contact agent" in lower or "call agent" in lower or "price on application" in lower or "poa" in lower:
        return PriceInfo(raw_text=raw, is_contact_agent=True)

    # Check for monthly indicator (pcm, per month, /month)
    is_monthly = bool(re.search(r'\b(pcm|per month|\/\s*month|calendar month)\b', lower))

    # Find dollar amounts
    matches = re.findall(r'\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)', raw)
    if not matches:
        return PriceInfo(raw_text=raw)

    nums = []
    for m in matches:
        try:
            val = int(m.replace(',', ''))
            if 80 <= val <= 25000:
                nums.append(val)
        except ValueError:
            pass

    if not nums:
        return PriceInfo(raw_text=raw)

    primary_num = nums[0]

    if is_monthly or primary_num > 3000:
        monthly = primary_num
        weekly = round(monthly * 12 / 52)
    else:
        weekly = primary_num
        monthly = round(weekly * 52 / 12)

    bond = weekly * 4 if weekly else None

    return PriceInfo(
        weekly=weekly,
        monthly=monthly,
        raw_text=raw,
        bond_amount=bond
    )

def parse_sale_price(text: str) -> PriceInfo:
    """Parses property sale prices or guides ($850,000, $1.2M, $950k-$1M)."""
    if not text:
        return PriceInfo(raw_text="")
    
    raw = text.strip()
    lower = raw.lower()

    # Match $1,250,000 or $850,000
    m = re.search(r'\$\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{5,9})', raw)
    if m:
        try:
            val = int(m.group(1).replace(',', ''))
            return PriceInfo(sale_price=val, raw_text=raw)
        except ValueError:
            pass

    # Match $1.25M or $850k
    m_k = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)\s*m\b', lower)
    if m_k:
        val = int(float(m_k.group(1)) * 1_000_000)
        return PriceInfo(sale_price=val, raw_text=raw)

    m_k2 = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)\s*k\b', lower)
    if m_k2:
        val = int(float(m_k2.group(1)) * 1_000)
        return PriceInfo(sale_price=val, raw_text=raw)

    return PriceInfo(raw_text=raw, is_contact_agent=True)

def detect_property_features(
    text: str = "",
    desc: str = "",
    explicit_type: Optional[str] = None
) -> PropertyFeatures:
    """
    Extracts bedrooms, bathrooms, cars, property type, and amenity tags (pets, pool, aircon).
    """
    combined = f"{text} {desc}".lower()

    # Beds
    beds = 1
    bm = re.search(r'(\d+)\s*(?:bed|bedroom|br\b)', combined)
    if bm:
        beds = max(1, min(10, int(bm.group(1))))
    elif "studio" in combined:
        beds = 0

    # Baths
    baths = 1
    bam = re.search(r'(\d+)\s*(?:bath|bathroom|ba\b)', combined)
    if bam:
        baths = max(1, min(8, int(bam.group(1))))

    # Cars
    cars = 1
    cm = re.search(r'(\d+)\s*(?:car|parking|garage|carport)', combined)
    if cm:
        cars = max(0, min(8, int(cm.group(1))))

    # Property Type
    prop_type = "House"
    if explicit_type:
        prop_type = explicit_type.title()
    else:
        types = ["Apartment", "Unit", "Townhouse", "Villa", "Studio", "Duplex", "Terrace", "House"]
        for pt in types:
            if pt.lower() in combined:
                prop_type = pt
                break

    # Pets allowed detection
    pets_allowed = 0
    if re.search(r'\b(no pets?|strictly no pets?|not suitable for pets?|pets? not permitted|pets? not allowed|sorry,? no pets?)\b', combined):
        pets_allowed = 0
    elif re.search(r'\b(pets?\s*(?:considered|allowed|welcome|friendly|ok|permitted|negotiable|approved|upon application|on application))\b', combined):
        pets_allowed = 1
    elif re.search(r'\b(dog|cat|pets?)\s*(?:friendly|allowed|welcome|ok)\b', combined):
        pets_allowed = 1

    # Additional features
    has_pool = bool(re.search(r'\b(pool|swimming pool|in-ground pool|plunge pool|lap pool)\b', combined))
    has_aircon = bool(re.search(r'\b(air conditioning|air con|air-con|split system|ducted air|cooling)\b', combined))
    has_yard = bool(re.search(r'\b(yard|backyard|courtyard|lawn|garden)\b', combined))
    is_furnished = bool(re.search(r'\b(fully furnished|furnished)\b', combined) and not re.search(r'\bunfurnished\b', combined))

    tags = []
    if pets_allowed: tags.append("pets")
    if has_pool: tags.append("pool")
    if has_aircon: tags.append("aircon")
    if has_yard: tags.append("yard")
    if is_furnished: tags.append("furnished")

    return PropertyFeatures(
        beds=beds,
        baths=baths,
        cars=cars,
        prop_type=prop_type,
        pets_allowed=pets_allowed,
        has_pool=has_pool,
        has_aircon=has_aircon,
        has_yard=has_yard,
        is_furnished=is_furnished,
        tags=tags
    )

def parse_inspection_datetime(raw_text: str) -> Optional[str]:
    """
    Parses messy inspection strings into ISO-8601 strings.
    Handles:
      - '2026-10-10T11:00:00+11:00'
      - 'Saturday 10 Oct 11:00AM - 11:30AM'
      - '10/10/2026 11:00 AM'
    """
    if not raw_text:
        return None
    raw = raw_text.strip()
    
    # Check if already ISO format
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', raw):
        return raw

    # Attempt to extract time and day/month
    # e.g., '10 Oct 11:00am'
    m = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})(?:\s+(\d{4}))?.*?(\d{1,2}):(\d{2})\s*(am|pm)?', raw, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month_str = m.group(2)[:3].capitalize()
        year = int(m.group(3)) if m.group(3) else datetime.now().year
        hour = int(m.group(4))
        minute = int(m.group(5))
        meridiem = (m.group(6) or "").lower()

        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0

        months = {
            "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
        }
        month = months.get(month_str, datetime.now().month)

        try:
            dt = datetime(year, month, day, hour, minute)
            return dt.isoformat() + "+11:00"
        except ValueError:
            pass

    return None
