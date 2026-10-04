import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException, BackgroundTasks, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
import database
import scraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("server")

app = FastAPI(title="2541 Rental Finder API", description="App for finding rentals in 2541 under $550/week")

# Initialize database on startup
database.init_db()

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

class ListingMetaUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    is_favorite: Optional[int] = None

class CustomListingInput(BaseModel):
    title: Optional[str] = None
    street: str
    suburb: str = "Nowra"
    postcode: str = "2541"
    price: int
    beds: int = 1
    baths: int = 1
    cars: int = 1
    prop_type: str = "House"
    url: Optional[str] = ""
    image_url: Optional[str] = ""
    inspection_date: Optional[str] = None
    description: Optional[str] = ""
    notes: Optional[str] = ""
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
            logger.info("Running scheduled background scrape for 2541 rentals...")
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
        if stats["total_all"] == 0:
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

@api.get("/listings")
def get_listings(
    max_price: Optional[int] = Query(550),
    suburb: Optional[str] = Query("all"),
    min_beds: Optional[int] = Query(0),
    min_baths: Optional[int] = Query(0),
    min_cars: Optional[int] = Query(0),
    prop_type: Optional[str] = Query("all"),
    status: Optional[str] = Query("all"),
    only_inspections: bool = Query(False),
    only_favorites: bool = Query(False),
    query: Optional[str] = Query(None),
    sort_by: str = Query("price_asc")
):
    items = database.get_listings(
        max_price=max_price,
        suburb=suburb,
        min_beds=min_beds,
        min_baths=min_baths,
        min_cars=min_cars,
        prop_type=prop_type,
        status=status,
        only_inspections=only_inspections,
        only_favorites=only_favorites,
        query=query,
        sort_by=sort_by
    )
    return {
        "count": len(items),
        "listings": items
    }

@api.get("/listings/{listing_id}")
def get_single_listing(listing_id: str):
    item = database.get_listing_by_id(listing_id)
    if not item:
        raise HTTPException(status_code=404, detail="Listing not found")
    return item

@api.post("/listings/refresh")
def refresh_listings():
    result = scraper.run_scraper_and_sync()
    stats = database.get_stats()
    return {
        "success": True,
        "scraped": result["total_scraped"],
        "newly_added": result["newly_added"],
        "stats": stats
    }

@api.patch("/listings/{listing_id}/meta")
def update_meta(listing_id: str, payload: ListingMetaUpdate):
    ok = database.update_listing_meta(
        listing_id,
        status=payload.status,
        notes=payload.notes,
        rating=payload.rating,
        is_favorite=payload.is_favorite
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Could not update listing meta")
    return {"success": True, "id": listing_id}

@api.post("/listings/mark-seen")
def mark_seen():
    database.mark_all_seen()
    return {"success": True}

@api.post("/listings/add")
def add_listing(payload: CustomListingInput):
    new_id = database.add_custom_listing(payload.dict())
    return {"success": True, "id": new_id}

@api.delete("/listings/{listing_id}")
def delete_listing(listing_id: str):
    ok = database.delete_listing(listing_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Listing not found or already deleted")
    return {"success": True}

@api.get("/stats")
def get_stats():
    return database.get_stats()

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
def get_portal_links(max_price: int = 550):
    return {
        "portals": [
            {
                "name": "Realestate.com.au",
                "tagline": "Australia's largest real estate portal",
                "category": "Major Portals",
                "icon": "home",
                "url": f"https://www.realestate.com.au/rent/with-maxPrice-{max_price}-in-2541/list-1?activeSort=list-date"
            },
            {
                "name": "Domain.com.au",
                "tagline": "Leading Australian property portal",
                "category": "Major Portals",
                "icon": "globe",
                "url": f"https://www.domain.com.au/rent/?postcode=2541&price=0-{max_price}&sort=dateupdated-desc"
            },
            {
                "name": "Rent.com.au",
                "tagline": "Renter-focused property directory",
                "category": "Major Portals",
                "icon": "key",
                "url": f"https://www.rent.com.au/properties/2541?price_max={max_price}"
            },
            {
                "name": "Allhomes.com.au",
                "tagline": "Popular for regional NSW and ACT",
                "category": "Major Portals",
                "icon": "compass",
                "url": f"https://www.allhomes.com.au/rent/nowra-nsw-2541/?price=0-{max_price}"
            },
            {
                "name": "Homely.com.au",
                "tagline": "Suburban reviews and rentals",
                "category": "Alternative Portals",
                "icon": "map-pin",
                "url": f"https://www.homely.com.au/for-rent/nowra-nsw-2541/properties?price=0-{max_price}"
            },
            {
                "name": "Gumtree Australia",
                "tagline": "Private landlord and direct rentals",
                "category": "Private & Share",
                "icon": "users",
                "url": f"https://www.gumtree.com.au/s-property-for-rent/nowra-2541/c18364l3000947?price=__{max_price}"
            },
            {
                "name": "Flatmates.com.au",
                "tagline": "Granny flats, studios & shared houses",
                "category": "Private & Share",
                "icon": "coffee",
                "url": f"https://flatmates.com.au/rent/nowra-2541?max_price={max_price}"
            },
            {
                "name": "Ray White Nowra",
                "tagline": "Local Shoalhaven agency rentals",
                "category": "Local Agencies",
                "icon": "building",
                "url": f"https://raywhiteshoalhavencentralgroup.com.au/properties/residential-for-rent?price_max={max_price}"
            },
            {
                "name": "Integrity Real Estate",
                "tagline": "Leading independent Nowra agency",
                "category": "Local Agencies",
                "icon": "award",
                "url": "https://www.integrityre.com.au/renting/properties-for-lease/"
            },
            {
                "name": "LJ Hooker Nowra",
                "tagline": "Kinghorne St Nowra office rentals",
                "category": "Local Agencies",
                "icon": "shield-check",
                "url": "https://nowra.ljhooker.com.au/search/property-for-rent/page-1"
            },
            {
                "name": "Raine & Horne Nowra",
                "tagline": "Shoalhaven regional leasing",
                "category": "Local Agencies",
                "icon": "briefcase",
                "url": f"https://www.raineandhorne.com.au/nowra/search/properties-for-rent?price_max={max_price}"
            }
        ]
    }

@api.get("/calendar/{listing_id}.ics")
def get_ics_calendar(listing_id: str):
    item = database.get_listing_by_id(listing_id)
    if not item or not item.get("inspection_date"):
        raise HTTPException(status_code=404, detail="No inspection date available for this listing")
        
    insp_iso = item["inspection_date"]
    clean_dt = insp_iso.replace("-", "").replace(":", "")[:15]
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//2541 Rental Finder//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
SUMMARY:Inspection: {item.get('street')}, {item.get('suburb')} (${item.get('price')}/wk)
DESCRIPTION:Rental property inspection in 2541.\\nPrice: ${item.get('price')}/wk\\nBeds: {item.get('beds')}, Baths: {item.get('baths')}\\nListing: {item.get('url')}
LOCATION:{item.get('street')}, {item.get('suburb')} NSW 2541
DTSTART:{clean_dt}
DTEND:{clean_dt}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""
    return Response(content=ics_content, media_type="text/calendar", headers={
        "Content-Disposition": f"attachment; filename=inspection-{listing_id}.ics"
    })

@api.get("/export/csv")
def export_csv(max_price: int = 550):
    items = database.get_listings(max_price=max_price)
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Price ($/wk)", "Street", "Suburb", "Postcode", "Beds", "Baths", "Cars",
        "Property Type", "Status", "Inspection Date", "Favorite", "Notes", "Listing URL"
    ])
    for it in items:
        writer.writerow([
            it.get("id"),
            it.get("price"),
            it.get("street"),
            it.get("suburb"),
            it.get("postcode"),
            it.get("beds"),
            it.get("baths"),
            it.get("cars"),
            it.get("prop_type"),
            it.get("status"),
            it.get("inspection_date"),
            "Yes" if it.get("is_favorite") else "No",
            it.get("notes"),
            it.get("url")
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rentals-2541.csv"}
    )

# Mount API router under both /api and root /
app.include_router(api, prefix="/api")
app.include_router(api, prefix="")

# Serve Frontend static assets when running standalone
if os.path.exists(STATIC_DIR) and not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
