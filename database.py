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
        postcode TEXT DEFAULT '2541',
        price INTEGER,
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
        first_seen TEXT,
        last_seen TEXT,
        price_history TEXT DEFAULT '[]'
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
            price = COALESCE(?, price),
            beds = COALESCE(?, beds),
            baths = COALESCE(?, baths),
            cars = COALESCE(?, cars),
            prop_type = COALESCE(?, prop_type),
            image_url = COALESCE(?, image_url),
            lat = COALESCE(?, lat),
            lng = COALESCE(?, lng),
            inspection_date = COALESCE(?, inspection_date),
            description = COALESCE(?, description),
            last_seen = ?,
            price_history = ?
        WHERE id = ?
        """, (
            item.get("title"),
            item.get("street"),
            item.get("suburb"),
            item.get("price"),
            item.get("beds"),
            item.get("baths"),
            item.get("cars"),
            item.get("prop_type"),
            item.get("image"),
            item.get("lat"),
            item.get("lng"),
            item.get("inspection"),
            item.get("desc"),
            now_str,
            json.dumps(history),
            current_id
        ))
    else:
        is_brand_new = True
        price = item.get("price")
        cursor.execute("""
        INSERT INTO listings (
            id, url, title, street, suburb, postcode, price, beds, baths, cars,
            prop_type, image_url, lat, lng, inspection_date, description,
            source, status, notes, rating, is_favorite, is_new, first_seen, last_seen, price_history
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered', '', 0, 0, 1, ?, ?, '[]')
        """, (
            lid,
            url,
            item.get("title"),
            item.get("street"),
            item.get("suburb", "Nowra"),
            item.get("postcode", "2541"),
            price,
            item.get("beds"),
            item.get("baths"),
            item.get("cars"),
            item.get("prop_type", "Unit"),
            item.get("image"),
            item.get("lat"),
            item.get("lng"),
            item.get("inspection"),
            item.get("desc"),
            item.get("source", "rent.com.au"),
            now_str,
            now_str
        ))
        
    conn.commit()
    conn.close()
    return is_brand_new

def get_listings(
    max_price: Optional[int] = None,
    suburb: Optional[str] = None,
    min_beds: Optional[int] = None,
    min_baths: Optional[int] = None,
    min_cars: Optional[int] = None,
    prop_type: Optional[str] = None,
    status: Optional[str] = None,
    only_inspections: bool = False,
    only_favorites: bool = False,
    query: Optional[str] = None,
    sort_by: str = "price_asc"
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT * FROM listings WHERE 1=1"
    params = []
    
    if max_price is not None:
        sql += " AND (price IS NULL OR price <= ?)"
        params.append(max_price)
        
    if suburb and suburb.lower() != "all":
        sql += " AND LOWER(suburb) = LOWER(?)"
        params.append(suburb)
        
    if min_beds is not None and min_beds > 0:
        sql += " AND beds >= ?"
        params.append(min_beds)
        
    if min_baths is not None and min_baths > 0:
        sql += " AND baths >= ?"
        params.append(min_baths)
        
    if min_cars is not None and min_cars > 0:
        sql += " AND cars >= ?"
        params.append(min_cars)
        
    if prop_type and prop_type.lower() != "all":
        sql += " AND LOWER(prop_type) = LOWER(?)"
        params.append(prop_type)
        
    if status and status.lower() != "all":
        sql += " AND status = ?"
        params.append(status)
        
    if only_inspections:
        sql += " AND inspection_date IS NOT NULL AND inspection_date != ''"
        
    if only_favorites:
        sql += " AND is_favorite = 1"
        
    if query:
        q = f"%{query}%"
        sql += " AND (title LIKE ? OR street LIKE ? OR suburb LIKE ? OR description LIKE ?)"
        params.extend([q, q, q, q])
        
    # Sorting
    if sort_by == "price_asc":
        sql += " ORDER BY price ASC, first_seen DESC"
    elif sort_by == "price_desc":
        sql += " ORDER BY price DESC, first_seen DESC"
    elif sort_by == "newest":
        sql += " ORDER BY first_seen DESC"
    elif sort_by == "beds_desc":
        sql += " ORDER BY beds DESC, price ASC"
    elif sort_by == "inspection":
        sql += " ORDER BY CASE WHEN inspection_date IS NULL OR inspection_date = '' THEN 1 ELSE 0 END, inspection_date ASC"
    else:
        sql += " ORDER BY price ASC"
        
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        d = dict(r)
        d["price_history"] = json.loads(d["price_history"] or "[]")
        results.append(d)
        
    conn.close()
    return results

def get_listing_by_id(lid: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE id = ?", (lid,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["price_history"] = json.loads(d["price_history"] or "[]")
        return d
    return None

def update_listing_meta(lid: str, status: Optional[str] = None, notes: Optional[str] = None,
                        rating: Optional[int] = None, is_favorite: Optional[int] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if rating is not None:
        updates.append("rating = ?")
        params.append(rating)
    if is_favorite is not None:
        updates.append("is_favorite = ?")
        params.append(is_favorite)
        
    if not updates:
        conn.close()
        return False
        
    params.append(lid)
    cursor.execute(f"UPDATE listings SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return True

def mark_all_seen():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE listings SET is_new = 0 WHERE is_new = 1")
    conn.commit()
    conn.close()

def add_custom_listing(data: Dict[str, Any]) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    import uuid
    lid = "manual_" + uuid.uuid4().hex[:8]
    now_str = datetime.now().isoformat()
    
    cursor.execute("""
    INSERT INTO listings (
        id, url, title, street, suburb, postcode, price, beds, baths, cars,
        prop_type, image_url, lat, lng, inspection_date, description,
        source, status, notes, rating, is_favorite, is_new, first_seen, last_seen, price_history
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', 'discovered', ?, 0, 1, 0, ?, ?, '[]')
    """, (
        lid,
        data.get("url", ""),
        data.get("title") or f"{data.get('street', 'Custom')}, {data.get('suburb', 'Nowra')}",
        data.get("street", ""),
        data.get("suburb", "Nowra"),
        data.get("postcode", "2541"),
        data.get("price", 0),
        data.get("beds", 1),
        data.get("baths", 1),
        data.get("cars", 1),
        data.get("prop_type", "House"),
        data.get("image_url", ""),
        data.get("lat") or -34.8727,
        data.get("lng") or 150.6019,
        data.get("inspection_date"),
        data.get("description", ""),
        data.get("notes", ""),
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

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE price <= 550")
    total_under_550 = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings")
    total_all = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(price), MIN(price), MAX(price) FROM listings WHERE price <= 550")
    avg_price, min_price, max_price_val = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE is_favorite = 1")
    favorites_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE inspection_date IS NOT NULL AND inspection_date != '' AND price <= 550")
    inspections_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE is_new = 1 AND price <= 550")
    new_count = cursor.fetchone()[0]
    
    cursor.execute("""
    SELECT suburb, COUNT(*), ROUND(AVG(price), 0)
    FROM listings
    WHERE price <= 550
    GROUP BY suburb
    ORDER BY COUNT(*) DESC
    """)
    suburbs = [{"suburb": r[0], "count": r[1], "avg_rent": r[2]} for r in cursor.fetchall()]
    
    cursor.execute("""
    SELECT prop_type, COUNT(*)
    FROM listings
    WHERE price <= 550
    GROUP BY prop_type
    ORDER BY COUNT(*) DESC
    """)
    property_types = [{"type": r[0], "count": r[1]} for r in cursor.fetchall()]
    
    conn.close()
    return {
        "total_under_550": total_under_550,
        "total_all": total_all,
        "avg_price": round(avg_price, 1) if avg_price else 0,
        "min_price": min_price or 0,
        "max_price": max_price_val or 0,
        "favorites_count": favorites_count,
        "inspections_count": inspections_count,
        "new_count": new_count,
        "suburbs": suburbs,
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
