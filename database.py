import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

import tempfile

DB_DIR = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("VERCEL"):
    temp_dir = tempfile.gettempdir()
    DB_PATH = os.path.join(temp_dir, "rentals_2541.db")
    repo_db = os.path.join(DB_DIR, "rentals_2541.db")
    if not os.path.exists(DB_PATH) and os.path.exists(repo_db):
        import shutil
        try:
            shutil.copyfile(repo_db, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = os.path.join(DB_DIR, "rentals_2541.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Listings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id TEXT PRIMARY KEY,
        url TEXT UNIQUE,
        title TEXT,
        street TEXT,
        suburb TEXT,
        state TEXT DEFAULT 'NSW',
        postcode TEXT DEFAULT '2541',
        price INTEGER,
        listing_type TEXT DEFAULT 'rent',
        beds INTEGER,
        baths INTEGER,
        cars INTEGER,
        prop_type TEXT,
        image_url TEXT,
        lat REAL,
        lng REAL,
        inspection_date TEXT,
        description TEXT,
        source TEXT DEFAULT 'rent.com.au',
        status TEXT DEFAULT 'discovered',
        notes TEXT DEFAULT '',
        rating INTEGER DEFAULT 0,
        is_favorite INTEGER DEFAULT 0,
        is_new INTEGER DEFAULT 1,
        pets_allowed INTEGER DEFAULT 0,
        features TEXT DEFAULT '[]',
        user_id TEXT DEFAULT 'public',
        first_seen TEXT,
        last_seen TEXT,
        price_history TEXT DEFAULT '[]'
    )
    """)
    
    # Schema migrations for Australia-wide support and user isolation
    migrations = [
        ("pets_allowed", "INTEGER DEFAULT 0"),
        ("listing_type", "TEXT DEFAULT 'rent'"),
        ("state", "TEXT DEFAULT 'NSW'"),
        ("features", "TEXT DEFAULT '[]'"),
        ("user_id", "TEXT DEFAULT 'public'")
    ]
    for col, col_def in migrations:
        try:
            cursor.execute(f"ALTER TABLE listings ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass

    # Ensure existing records have default values
    cursor.execute("UPDATE listings SET listing_type = 'rent' WHERE listing_type IS NULL OR listing_type = ''")
    cursor.execute("UPDATE listings SET state = 'NSW' WHERE state IS NULL OR state = ''")
    cursor.execute("UPDATE listings SET user_id = 'public' WHERE user_id IS NULL OR user_id = ''")
    cursor.execute("UPDATE listings SET features = '[]' WHERE features IS NULL OR features = ''")

    # Mark verified pet friendly listings
    pet_addresses = [
        '%St Anns%',
        '%Sampson%',
        '%16 Stuart%',
        '%5 Burr%',
        '%22 Mcmahons%',
        '%1/2 Mcmahons%',
        '%Aspromonte%',
        '%Mattes Way%',
        '%Wondalga%',
        '%Castle Glen%',
        '%Curta Place%',
        '%Kauri Street%'
    ]
    for addr in pet_addresses:
        cursor.execute("UPDATE listings SET pets_allowed = 1 WHERE street LIKE ?", (addr,))

    # User interactions table for cookie-isolated personal workspaces
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_interactions (
        user_id TEXT,
        listing_id TEXT,
        is_favorite INTEGER DEFAULT 0,
        status TEXT DEFAULT 'discovered',
        notes TEXT DEFAULT '',
        rating INTEGER DEFAULT 0,
        updated_at TEXT,
        PRIMARY KEY (user_id, listing_id)
    )
    """)

    # Settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    # Default settings
    default_settings = {
        "max_price": "550",
        "suburb_filter": "all",
        "auto_refresh_interval": "30",
        "sound_enabled": "true",
        "desktop_notifications": "true",
        "webhook_url": ""
    }
    
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    # Seed Australia-wide properties (Houses for Sale & Metro Rentals)
    try:
        from seed_data import AUSTRALIA_LISTINGS
        now_str = datetime.now().isoformat()
        for item in AUSTRALIA_LISTINGS:
            cursor.execute("SELECT id FROM listings WHERE id = ?", (item["id"],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO listings (
                    id, url, title, street, suburb, state, postcode, price,
                    listing_type, beds, baths, cars, prop_type, image_url,
                    lat, lng, inspection_date, description, source, status,
                    notes, rating, is_favorite, is_new, pets_allowed,
                    features, user_id, first_seen, last_seen, price_history
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered', '', 0, 0, 1, ?, ?, 'public', ?, ?, '[]')
                """, (
                    item["id"],
                    item["url"],
                    item["title"],
                    item["street"],
                    item["suburb"],
                    item.get("state", "NSW"),
                    item.get("postcode", "2000"),
                    item.get("price", 0),
                    item.get("listing_type", "sale"),
                    item.get("beds", 1),
                    item.get("baths", 1),
                    item.get("cars", 1),
                    item.get("prop_type", "House"),
                    item.get("image_url", ""),
                    item.get("lat", -33.8688),
                    item.get("lng", 151.2093),
                    item.get("inspection_date"),
                    item.get("description", ""),
                    item.get("source", "domain.com.au"),
                    item.get("pets_allowed", 0),
                    json.dumps(item.get("features", [])),
                    now_str,
                    now_str
                ))
    except Exception as e:
        print(f"Australia seed notice: {e}")

    conn.commit()
    conn.close()

def upsert_listing(item: Dict[str, Any]) -> bool:
    """
    Inserts or updates a listing.
    Returns True if this is a brand new listing under or equal to max price, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    url = item.get("url")
    lid = item.get("id") or str(hash(url))
    
    cursor.execute("SELECT id, price, price_history, is_new FROM listings WHERE url = ? OR id = ?", (url, lid))
    existing = cursor.fetchone()
    
    is_brand_new = False
    
    if existing:
        current_id = existing["id"]
        old_price = existing["price"]
        history = json.loads(existing["price_history"] or "[]")
        new_price = item.get("price")
        
        if new_price and old_price and new_price != old_price:
            history.append({
                "date": now_str,
                "old": old_price,
                "new": new_price
            })
            
        cursor.execute("""
        UPDATE listings SET
            title = COALESCE(?, title),
            street = COALESCE(?, street),
            suburb = COALESCE(?, suburb),
            state = COALESCE(?, state),
            price = COALESCE(?, price),
            listing_type = COALESCE(?, listing_type),
            beds = COALESCE(?, beds),
            baths = COALESCE(?, baths),
            cars = COALESCE(?, cars),
            prop_type = COALESCE(?, prop_type),
            image_url = COALESCE(?, image_url),
            lat = COALESCE(?, lat),
            lng = COALESCE(?, lng),
            inspection_date = COALESCE(?, inspection_date),
            description = COALESCE(?, description),
            pets_allowed = COALESCE(?, pets_allowed),
            features = COALESCE(?, features),
            last_seen = ?,
            price_history = ?
        WHERE id = ?
        """, (
            item.get("title"),
            item.get("street"),
            item.get("suburb"),
            item.get("state", "NSW"),
            item.get("price"),
            item.get("listing_type", "rent"),
            item.get("beds"),
            item.get("baths"),
            item.get("cars"),
            item.get("prop_type"),
            item.get("image_url"),
            item.get("lat"),
            item.get("lng"),
            item.get("inspection_date"),
            item.get("description"),
            item.get("pets_allowed", 0),
            json.dumps(item.get("features", [])) if "features" in item else None,
            now_str,
            json.dumps(history),
            current_id
        ))
    else:
        is_brand_new = True
        cursor.execute("""
        INSERT INTO listings (
            id, url, title, street, suburb, state, postcode, price,
            listing_type, beds, baths, cars, prop_type, image_url,
            lat, lng, inspection_date, description, source, status,
            notes, rating, is_favorite, is_new, pets_allowed,
            features, user_id, first_seen, last_seen, price_history
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered', '', 0, 0, 1, ?, ?, 'public', ?, ?, '[]')
        """, (
            lid,
            url,
            item.get("title") or f"{item.get('street', '')}, {item.get('suburb', '')}",
            item.get("street", ""),
            item.get("suburb", ""),
            item.get("state", "NSW"),
            item.get("postcode", "2541"),
            item.get("price"),
            item.get("listing_type", "rent"),
            item.get("beds", 1),
            item.get("baths", 1),
            item.get("cars", 1),
            item.get("prop_type", "House"),
            item.get("image_url", ""),
            item.get("lat"),
            item.get("lng"),
            item.get("inspection_date"),
            item.get("description", ""),
            item.get("source", "rent.com.au"),
            item.get("pets_allowed", 0),
            json.dumps(item.get("features", [])),
            now_str,
            now_str
        ))
        
    conn.commit()
    conn.close()
    return is_brand_new

def get_listings(
    listing_type: Optional[str] = "all",
    state: Optional[str] = "all",
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    suburb: Optional[str] = None,
    min_beds: Optional[int] = None,
    min_baths: Optional[int] = None,
    min_cars: Optional[int] = None,
    prop_type: Optional[str] = None,
    status: Optional[str] = None,
    only_inspections: bool = False,
    only_favorites: bool = False,
    only_pets: bool = False,
    only_pool: bool = False,
    only_aircon: bool = False,
    query: Optional[str] = None,
    sort_by: str = "price_asc",
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    current_uid = user_id or "guest"
    
    # Left join user_interactions to isolate each user's favorites, notes, pipeline stage
    sql = """
    SELECT 
        l.id, l.url, l.title, l.street, l.suburb, l.state, l.postcode, l.price,
        l.listing_type, l.beds, l.baths, l.cars, l.prop_type, l.image_url,
        l.lat, l.lng, l.inspection_date, l.description, l.source,
        COALESCE(ui.status, l.status) AS status,
        COALESCE(ui.notes, '') AS notes,
        COALESCE(ui.rating, 0) AS rating,
        COALESCE(ui.is_favorite, 0) AS is_favorite,
        l.is_new, l.pets_allowed, l.features, l.user_id, l.first_seen, l.last_seen, l.price_history
    FROM listings l
    LEFT JOIN user_interactions ui 
        ON ui.listing_id = l.id AND ui.user_id = ?
    WHERE (l.user_id = 'public' OR l.user_id = ?)
    """
    params = [current_uid, current_uid]
    
    # Listing type: rent vs sale
    if listing_type and listing_type.lower() != "all":
        sql += " AND LOWER(l.listing_type) = LOWER(?)"
        params.append(listing_type)
        
    # State filter
    if state and state.lower() != "all":
        sql += " AND LOWER(l.state) = LOWER(?)"
        params.append(state)
        
    # Min & Max Price
    if min_price is not None and min_price > 0:
        sql += " AND (l.price IS NOT NULL AND l.price >= ?)"
        params.append(min_price)
        
    if max_price is not None and max_price > 0:
        sql += " AND (l.price IS NULL OR l.price <= ?)"
        params.append(max_price)
        
    # Suburb / Location
    if suburb and suburb.lower() != "all":
        sql += " AND (LOWER(l.suburb) = LOWER(?) OR LOWER(l.postcode) = LOWER(?))"
        params.extend([suburb, suburb])
        
    # Bedrooms, Baths, Cars
    if min_beds is not None and min_beds > 0:
        sql += " AND l.beds >= ?"
        params.append(min_beds)
        
    if min_baths is not None and min_baths > 0:
        sql += " AND l.baths >= ?"
        params.append(min_baths)
        
    if min_cars is not None and min_cars > 0:
        sql += " AND l.cars >= ?"
        params.append(min_cars)
        
    if prop_type and prop_type.lower() != "all":
        sql += " AND LOWER(l.prop_type) = LOWER(?)"
        params.append(prop_type)
        
    # Status / Pipeline (User isolated)
    if status and status.lower() != "all":
        sql += " AND COALESCE(ui.status, l.status) = ?"
        params.append(status)
        
    if only_inspections:
        sql += " AND l.inspection_date IS NOT NULL AND l.inspection_date != ''"
        
    if only_favorites:
        sql += " AND COALESCE(ui.is_favorite, 0) = 1"
        
    if only_pets:
        sql += " AND l.pets_allowed = 1"
        
    if only_pool:
        sql += " AND (l.features LIKE '%pool%' OR l.description LIKE '%pool%')"
        
    if only_aircon:
        sql += " AND (l.features LIKE '%aircon%' OR l.description LIKE '%air%conditioning%' OR l.description LIKE '%ac%')"
        
    if query:
        q = f"%{query.strip()}%"
        sql += " AND (l.title LIKE ? OR l.street LIKE ? OR l.suburb LIKE ? OR l.state LIKE ? OR l.postcode LIKE ? OR l.description LIKE ?)"
        params.extend([q, q, q, q, q, q])
        
    # Sorting
    if sort_by == "price_asc":
        sql += " ORDER BY l.price ASC, l.first_seen DESC"
    elif sort_by == "price_desc":
        sql += " ORDER BY l.price DESC, l.first_seen DESC"
    elif sort_by == "newest":
        sql += " ORDER BY l.first_seen DESC"
    elif sort_by == "beds_desc":
        sql += " ORDER BY l.beds DESC, l.price ASC"
    elif sort_by == "inspection":
        sql += " ORDER BY CASE WHEN l.inspection_date IS NULL OR l.inspection_date = '' THEN 1 ELSE 0 END, l.inspection_date ASC"
    else:
        sql += " ORDER BY l.price ASC"
        
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        d = dict(r)
        d["price_history"] = json.loads(d["price_history"] or "[]")
        try:
            d["features"] = json.loads(d.get("features") or "[]")
        except Exception:
            d["features"] = []
        results.append(d)
        
    conn.close()
    return results

def get_listing_by_id(lid: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    current_uid = user_id or "guest"
    
    sql = """
    SELECT 
        l.id, l.url, l.title, l.street, l.suburb, l.state, l.postcode, l.price,
        l.listing_type, l.beds, l.baths, l.cars, l.prop_type, l.image_url,
        l.lat, l.lng, l.inspection_date, l.description, l.source,
        COALESCE(ui.status, l.status) AS status,
        COALESCE(ui.notes, '') AS notes,
        COALESCE(ui.rating, 0) AS rating,
        COALESCE(ui.is_favorite, 0) AS is_favorite,
        l.is_new, l.pets_allowed, l.features, l.user_id, l.first_seen, l.last_seen, l.price_history
    FROM listings l
    LEFT JOIN user_interactions ui 
        ON ui.listing_id = l.id AND ui.user_id = ?
    WHERE l.id = ?
    """
    cursor.execute(sql, (current_uid, lid))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["price_history"] = json.loads(d["price_history"] or "[]")
        try:
            d["features"] = json.loads(d.get("features") or "[]")
        except Exception:
            d["features"] = []
        return d
    return None

def update_listing_meta(
    lid: str, 
    user_id: str = "guest",
    status: Optional[str] = None, 
    notes: Optional[str] = None,
    rating: Optional[int] = None, 
    is_favorite: Optional[int] = None,
    pets_allowed: Optional[int] = None
) -> bool:
    """
    Saves personal interactions per cookie user_id so every individual visitor only sees their own shortlist and notes.
    """
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    # Check if user interaction row already exists
    cursor.execute("SELECT is_favorite, status, notes, rating FROM user_interactions WHERE user_id = ? AND listing_id = ?", (user_id, lid))
    existing = cursor.fetchone()
    
    if existing:
        new_fav = is_favorite if is_favorite is not None else existing["is_favorite"]
        new_status = status if status is not None else existing["status"]
        new_notes = notes if notes is not None else existing["notes"]
        new_rating = rating if rating is not None else existing["rating"]
        cursor.execute("""
        UPDATE user_interactions SET
            is_favorite = ?,
            status = ?,
            notes = ?,
            rating = ?,
            updated_at = ?
        WHERE user_id = ? AND listing_id = ?
        """, (new_fav, new_status, new_notes, new_rating, now_str, user_id, lid))
    else:
        cursor.execute("""
        INSERT INTO user_interactions (user_id, listing_id, is_favorite, status, notes, rating, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            lid,
            is_favorite if is_favorite is not None else 0,
            status if status is not None else "discovered",
            notes if notes is not None else "",
            rating if rating is not None else 0,
            now_str
        ))
        
    if pets_allowed is not None:
        cursor.execute("UPDATE listings SET pets_allowed = ? WHERE id = ?", (pets_allowed, lid))
        
    conn.commit()
    conn.close()
    return True

def mark_all_seen():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE listings SET is_new = 0 WHERE is_new = 1")
    conn.commit()
    conn.close()

def add_custom_listing(data: Dict[str, Any], user_id: str = "public") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    import uuid
    lid = "manual_" + uuid.uuid4().hex[:8]
    now_str = datetime.now().isoformat()
    
    cursor.execute("""
    INSERT INTO listings (
        id, url, title, street, suburb, state, postcode, price,
        listing_type, beds, baths, cars, prop_type, image_url,
        lat, lng, inspection_date, description, source, status,
        notes, rating, is_favorite, is_new, pets_allowed,
        features, user_id, first_seen, last_seen, price_history
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered', ?, 0, 1, 0, ?, ?, ?, ?, ?, '[]')
    """, (
        lid,
        data.get("url", ""),
        data.get("title") or f"{data.get('street', 'Custom')}, {data.get('suburb', 'Nowra')}",
        data.get("street", ""),
        data.get("suburb", "Nowra"),
        data.get("state", "NSW"),
        data.get("postcode", "2541"),
        data.get("price", 0),
        data.get("listing_type", "rent"),
        data.get("beds", 1),
        data.get("baths", 1),
        data.get("cars", 1),
        data.get("prop_type", "House"),
        data.get("image_url", ""),
        data.get("lat") or -34.8727,
        data.get("lng") or 150.6019,
        data.get("inspection_date"),
        data.get("description", ""),
        "manual",
        data.get("notes", ""),
        data.get("pets_allowed", 0),
        json.dumps(data.get("features", [])),
        user_id,
        now_str,
        now_str
    ))
    conn.commit()
    conn.close()
    return lid

def delete_listing(lid: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM listings WHERE id = ?", (lid,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_stats(listing_type: str = "all", state: Optional[str] = None, user_id: str = "guest") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    where_clauses = ["(user_id = 'public' OR user_id = ?)"]
    params = [user_id]
    
    if listing_type and listing_type != "all":
        where_clauses.append("LOWER(listing_type) = LOWER(?)")
        params.append(listing_type)
        
    if state and state != "all":
        where_clauses.append("LOWER(state) = LOWER(?)")
        params.append(state)
        
    where_sql = " AND ".join(where_clauses)
    
    cursor.execute(f"SELECT COUNT(*) FROM listings WHERE {where_sql}", params)
    total_count = cursor.fetchone()[0]
    
    # Rent vs Sale counts
    cursor.execute("SELECT COUNT(*) FROM listings WHERE listing_type = 'rent'")
    rent_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE listing_type = 'sale'")
    sale_count = cursor.fetchone()[0]
    
    # Averages
    cursor.execute("SELECT AVG(price), MIN(price), MAX(price) FROM listings WHERE listing_type = 'rent'")
    avg_rent, min_rent, max_rent = cursor.fetchone()
    
    cursor.execute("SELECT AVG(price), MIN(price), MAX(price) FROM listings WHERE listing_type = 'sale'")
    avg_sale, min_sale, max_sale = cursor.fetchone()
    
    # User-specific favorites count
    cursor.execute("SELECT COUNT(*) FROM user_interactions WHERE user_id = ? AND is_favorite = 1", (user_id,))
    favorites_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE inspection_date IS NOT NULL AND inspection_date != ''")
    inspections_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE pets_allowed = 1")
    pets_count = cursor.fetchone()[0]
    
    cursor.execute("""
    SELECT suburb, state, COUNT(*), ROUND(AVG(price), 0), listing_type
    FROM listings
    GROUP BY suburb, state, listing_type
    ORDER BY COUNT(*) DESC
    LIMIT 20
    """)
    suburbs = [{"suburb": r[0], "state": r[1], "count": r[2], "avg_price": r[3], "type": r[4]} for r in cursor.fetchall()]
    
    cursor.execute("""
    SELECT prop_type, COUNT(*)
    FROM listings
    GROUP BY prop_type
    ORDER BY COUNT(*) DESC
    """)
    property_types = [{"type": r[0], "count": r[1]} for r in cursor.fetchall()]

    cursor.execute("""
    SELECT state, COUNT(*)
    FROM listings
    GROUP BY state
    ORDER BY COUNT(*) DESC
    """)
    states = [{"state": r[0], "count": r[1]} for r in cursor.fetchall()]
    
    conn.close()
    return {
        "total": total_count,
        "rent_count": rent_count,
        "sale_count": sale_count,
        "avg_rent": round(avg_rent, 1) if avg_rent else 0,
        "avg_sale": round(avg_sale, 0) if avg_sale else 0,
        "min_rent": min_rent or 0,
        "max_rent": max_rent or 0,
        "min_sale": min_sale or 0,
        "max_sale": max_sale or 0,
        "favorites_count": favorites_count,
        "inspections_count": inspections_count,
        "pets_count": pets_count,
        "suburbs": suburbs,
        "states": states,
        "property_types": property_types
    }

def get_settings() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {r["key"]: r["value"] for r in cursor.fetchall()}
    conn.close()
    return settings

def update_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
