import os
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
import database
import scraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

app = FastAPI(
    title="Radar Realty Australia API",
    description="Australia-wide real estate search, rental tracker, and properties for sale"
)

# Initialize database on startup
database.init_db()

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

def get_effective_user_id(request: Request, response: Response, explicit_user_id: Optional[str] = None) -> str:
    """
    Retrieves or generates a persistent cookie user_id to isolate each visitor's workspace.
    """
    uid = explicit_user_id or request.headers.get("x-user-id") or request.cookies.get("radar_user_token")
    if not uid or len(uid.strip()) == 0:
        uid = f"usr_{uuid.uuid4().hex[:12]}"
        
    # Ensure cookie is set for long-term persistence (1 year)
    if "radar_user_token" not in request.cookies or request.cookies.get("radar_user_token") != uid:
        response.set_cookie(
            key="radar_user_token",
            value=uid,
            max_age=31536000,
            httponly=False,
            samesite="lax",
            path="/"
        )
    return uid

class ListingMetaUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    is_favorite: Optional[int] = None
    pets_allowed: Optional[int] = None

class CustomListingInput(BaseModel):
    title: Optional[str] = None
    street: str
    suburb: str = "Sydney"
    state: str = "NSW"
    postcode: str = "2000"
    price: int
    listing_type: str = "rent" # 'rent' or 'sale'
    beds: int = 1
    baths: int = 1
    cars: int = 1
    prop_type: str = "House"
    url: Optional[str] = ""
    image_url: Optional[str] = ""
    inspection_date: Optional[str] = None
    description: Optional[str] = ""
    notes: Optional[str] = ""
    pets_allowed: Optional[int] = 0
    features: Optional[List[str]] = []
    lat: Optional[float] = None
    lng: Optional[float] = None

class SettingsUpdate(BaseModel):
    max_price: Optional[str] = None
    suburb_filter: Optional[str] = None
    auto_refresh_interval: Optional[str] = None
    sound_enabled: Optional[str] = None
    desktop_notifications: Optional[str] = None
    webhook_url: Optional[str] = None

# Background Periodic Refresh Task
_periodic_task = None

async def periodic_scraper():
    while True:
        try:
            settings = database.get_settings()
            interval_mins = int(settings.get("auto_refresh_interval", "30"))
            if interval_mins <= 0:
                interval_mins = 30
            await asyncio.sleep(interval_mins * 60)
            logger.info("Running scheduled background scrape for Australian rentals...")
            result = scraper.run_scraper_and_sync()
            logger.info(f"Scheduled sync complete: {result['total_scraped']} scraped, {result['newly_added']} new.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic scraper: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    global _periodic_task
    database.init_db()
    if not os.environ.get("VERCEL"):
        # Run initial sync if DB is empty
        stats = database.get_stats()
        if stats["total"] == 0:
            logger.info("Database empty on startup. Triggering initial scrape...")
            scraper.run_scraper_and_sync()
        _periodic_task = asyncio.create_task(periodic_scraper())

@app.on_event("shutdown")
async def shutdown_event():
    global _periodic_task
    if _periodic_task:
        _periodic_task.cancel()

# --- API Endpoints ---
from fastapi import APIRouter

api = APIRouter()

@api.get("/user/me")
def get_current_user(request: Request, response: Response, user_id: Optional[str] = None):
    uid = get_effective_user_id(request, response, user_id)
    return {"user_id": uid}

@api.get("/listings")
def get_listings(
    request: Request,
    response: Response,
    listing_type: Optional[str] = "all",
    state: Optional[str] = "all",
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    suburb: Optional[str] = "all",
    min_beds: Optional[int] = 0,
    min_baths: Optional[int] = 0,
    min_cars: Optional[int] = 0,
    prop_type: Optional[str] = "all",
    status: Optional[str] = "all",
    only_inspections: bool = False,
    only_favorites: bool = False,
    only_pets: bool = False,
    only_pool: bool = False,
    only_aircon: bool = False,
    query: Optional[str] = None,
    sort_by: str = "price_asc",
    user_id: Optional[str] = None
):
    uid = get_effective_user_id(request, response, user_id)
    
    items = database.get_listings(
        listing_type=listing_type,
        state=state,
        min_price=min_price,
        max_price=max_price,
        suburb=suburb,
        min_beds=min_beds,
        min_baths=min_baths,
        min_cars=min_cars,
        prop_type=prop_type,
        status=status,
        only_inspections=only_inspections,
        only_favorites=only_favorites,
        only_pets=only_pets,
        only_pool=only_pool,
        only_aircon=only_aircon,
        query=query,
        sort_by=sort_by,
        user_id=uid
    )
    return {
        "count": len(items),
        "user_id": uid,
        "listings": items
    }

@api.get("/listings/{listing_id}")
def get_single_listing(listing_id: str, request: Request, response: Response, user_id: Optional[str] = None):
    uid = get_effective_user_id(request, response, user_id)
    item = database.get_listing_by_id(listing_id, user_id=uid)
    if not item:
        raise HTTPException(status_code=404, detail="Listing not found")
    return item

@api.post("/listings/refresh")
def refresh_listings(request: Request, response: Response, user_id: Optional[str] = None):
    uid = get_effective_user_id(request, response, user_id)
    result = scraper.run_scraper_and_sync()
    stats = database.get_stats(user_id=uid)
    return {
        "success": True,
        "scraped": result["total_scraped"],
        "newly_added": result["newly_added"],
        "stats": stats
    }

@api.patch("/listings/{listing_id}/meta")
def update_meta(listing_id: str, payload: ListingMetaUpdate, request: Request, response: Response, user_id: Optional[str] = None):
    uid = get_effective_user_id(request, response, user_id)
    ok = database.update_listing_meta(
        listing_id,
        user_id=uid,
        status=payload.status,
        notes=payload.notes,
        rating=payload.rating,
        is_favorite=payload.is_favorite,
        pets_allowed=payload.pets_allowed
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Could not update listing meta")
    return {"success": True, "id": listing_id, "user_id": uid}

@api.post("/listings/mark-seen")
def mark_seen():
    database.mark_all_seen()
    return {"success": True}

@api.post("/listings/add")
def add_listing(payload: CustomListingInput, request: Request, response: Response, user_id: Optional[str] = None):
    uid = get_effective_user_id(request, response, user_id)
    new_id = database.add_custom_listing(payload.dict(), user_id=uid)
    return {"success": True, "id": new_id, "user_id": uid}

@api.delete("/listings/{listing_id}")
def delete_listing(listing_id: str):
    ok = database.delete_listing(listing_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Listing not found or already deleted")
    return {"success": True}

@api.get("/stats")
def get_stats(request: Request, response: Response, listing_type: str = "all", state: Optional[str] = None, user_id: Optional[str] = None):
    uid = get_effective_user_id(request, response, user_id)
    return database.get_stats(listing_type=listing_type, state=state, user_id=uid)

@api.get("/settings")
def get_settings():
    return database.get_settings()

@api.post("/settings")
def save_settings(payload: SettingsUpdate):
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            database.update_setting(k, str(v))
    return {"success": True, "settings": database.get_settings()}

@api.get("/portal-links")
def get_portal_links(listing_type: str = "rent", max_price: Optional[int] = None, suburb: Optional[str] = None):
    is_sale = listing_type == "sale"
    mode_str = "buy" if is_sale else "rent"
    price_val = max_price or (1500000 if is_sale else 550)
    loc_str = suburb if suburb and suburb != "all" else "Australia"
    loc_query = suburb if suburb and suburb != "all" else "australia"
    
    return {
        "mode": listing_type,
        "portals": [
            {
                "name": "Realestate.com.au",
                "tagline": f"Australia's #1 portal for properties to {mode_str}",
                "category": "Major Portals",
                "icon": "home",
                "url": f"https://www.realestate.com.au/{mode_str}/in-{loc_query}/list-1?activeSort=list-date"
            },
            {
                "name": "Domain.com.au",
                "tagline": f"Premium Australian listings to {mode_str}",
                "category": "Major Portals",
                "icon": "globe",
                "url": f"https://www.domain.com.au/{mode_str}/?search={loc_query}&sort=dateupdated-desc"
            },
            {
                "name": "Rent.com.au" if not is_sale else "Soho Real Estate",
                "tagline": "Renter-dedicated directory" if not is_sale else "Fast property search & social alerts",
                "category": "Major Portals",
                "icon": "key" if not is_sale else "compass",
                "url": f"https://www.rent.com.au/properties/{loc_query}" if not is_sale else f"https://soho.com.au/{mode_str}"
            },
            {
                "name": "Allhomes.com.au",
                "tagline": "Leading portal across Regional NSW, ACT & Sydney",
                "category": "Major Portals",
                "icon": "compass",
                "url": f"https://www.allhomes.com.au/{mode_str}/"
            },
            {
                "name": "Homely.com.au",
                "tagline": "Suburban street reviews and property listings",
                "category": "Alternative Portals",
                "icon": "map-pin",
                "url": f"https://www.homely.com.au/for-{mode_str}/"
            },
            {
                "name": "Ray White Group",
                "tagline": "Australia's largest real estate franchise network",
                "category": "Local Agencies",
                "icon": "building",
                "url": f"https://www.raywhite.com/properties/{mode_str}"
            }
        ]
    }

@api.get("/calendar/{listing_id}.ics")
def get_calendar_invite(listing_id: str):
    item = database.get_listing_by_id(listing_id)
    if not item or not item.get("inspection_date"):
        raise HTTPException(status_code=404, detail="No inspection date found for this listing")
    
    from datetime import datetime, timedelta
    try:
        insp_dt = datetime.fromisoformat(item["inspection_date"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid inspection date format")
        
    start_str = insp_dt.strftime("%Y%m%dT%H%M%S")
    end_dt = insp_dt + timedelta(minutes=30)
    end_str = end_dt.strftime("%Y%m%dT%H%M%S")
    
    summary = f"Inspection: {item['street']}, {item['suburb']} ({item['prop_type']})"
    description = f"Rental inspection for {item['street']}, {item['suburb']}. Price: ${item['price']}/wk. Beds: {item['beds']}, Baths: {item['baths']}."
    location = f"{item['street']}, {item['suburb']} {item.get('state', 'NSW')} {item.get('postcode', '')}".strip()
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Australia Property Radar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:{location}
DTSTART:{start_str}
DTEND:{end_str}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=inspection_{item['id']}.ics"}
    )

@api.get("/export/csv")
def export_csv(
    request: Request,
    response: Response,
    listing_type: str = "all",
    max_price: Optional[int] = None,
    user_id: Optional[str] = None
):
    import csv
    import io
    
    uid = get_effective_user_id(request, response, user_id)
    listings = database.get_listings(listing_type=listing_type, max_price=max_price, user_id=uid)
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "ID", "Type", "Street", "Suburb", "State", "Postcode", "Price",
        "Beds", "Baths", "Cars", "Property Type", "Pets Allowed",
        "Inspection Date", "Status", "My Notes", "My Rating", "URL"
    ])
    
    for l in listings:
        writer.writerow([
            l["id"],
            l.get("listing_type", "rent").upper(),
            l["street"],
            l["suburb"],
            l.get("state", "NSW"),
            l["postcode"],
            l["price"],
            l["beds"],
            l["baths"],
            l["cars"],
            l["prop_type"],
            "Yes" if l.get("pets_allowed") == 1 else "No",
            l["inspection_date"] or "None scheduled",
            l["status"],
            l["notes"],
            l["rating"],
            l["url"]
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=radar_properties_export.csv"}
    )

app.include_router(api, prefix="/api")

# Static frontend assets
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
