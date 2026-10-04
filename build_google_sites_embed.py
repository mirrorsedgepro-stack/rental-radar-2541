import json
import os
import database

def build_embed():
    database.init_db()
    listings = database.get_listings(listing_type="all")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")
    
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
        
    with open(os.path.join(static_dir, "style.css"), "r", encoding="utf-8") as f:
        css = f.read()
        
    with open(os.path.join(static_dir, "app.js"), "r", encoding="utf-8") as f:
        js = f.read()
        
    listings_json = json.dumps(listings, ensure_ascii=False)
    
    # Custom Google Sites styling
    google_sites_css = """
        /* Google Sites Embed Optimization */
        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
            background-color: #f8fafc;
        }
    """
    full_css = css + "\n" + google_sites_css
    
    # Replace style link with inline style
    html = html.replace(
        '<link rel="stylesheet" href="style.css">',
        f'<style>\n{full_css}\n</style>'
    )
    
    # Embed initial listings and offline-first fallback in JS
    embedded_js = f"""
    // Pre-baked live listings for Google Sites (Australia-wide Rent & Sale)
    const INITIAL_LISTINGS = {listings_json};

    // Override fetchListings for offline/iframe embedding if local API is unreachable
    const originalFetchListings = window.fetchListings;
    """ + js.replace(
        "allListings = data.listings || [];",
        """allListings = (data.listings && data.listings.length > 0) ? data.listings : INITIAL_LISTINGS;
        localStorage.setItem('property_radar_listings', JSON.stringify(allListings));"""
    ).replace(
        "let storedListings = [];",
        "let storedListings = JSON.parse(localStorage.getItem('property_radar_listings') || 'null') || INITIAL_LISTINGS;"
    ).replace(
        "allListings = [];",
        "allListings = JSON.parse(localStorage.getItem('property_radar_listings') || 'null') || INITIAL_LISTINGS;"
    )

    # In case the iframe cannot talk to /api, fallback to INITIAL_LISTINGS
    fallback_patch = """
    // Google Sites Fallback: if fetch fails, use embedded listings
    const origFetch = window.fetch;
    window.fetch = async function(...args) {
        try {
            return await origFetch.apply(this, args);
        } catch(e) {
            console.log("Using embedded dataset:", args[0]);
            const url = args[0] || '';
            if (url.includes('/api/listings')) {
                let items = [...INITIAL_LISTINGS];
                try {
                    const parsedUrl = new URL(url, 'http://localhost');
                    const mode = parsedUrl.searchParams.get('listing_type');
                    if (mode && mode !== 'all') items = items.filter(l => (l.listing_type || 'rent').toLowerCase() === mode.toLowerCase());
                    const state = parsedUrl.searchParams.get('state');
                    if (state && state !== 'all') items = items.filter(l => (l.state || '').toLowerCase() === state.toLowerCase());
                    const maxP = parseInt(parsedUrl.searchParams.get('max_price') || '0');
                    if (maxP > 0) items = items.filter(l => (l.price || 0) <= maxP);
                    const sub = parsedUrl.searchParams.get('suburb');
                    if (sub && sub !== 'all') items = items.filter(l => (l.suburb || '').toLowerCase() === sub.toLowerCase());
                    const beds = parseInt(parsedUrl.searchParams.get('min_beds') || '0');
                    if (beds > 0) items = items.filter(l => (l.beds || 0) >= beds);
                    const ptype = parsedUrl.searchParams.get('prop_type');
                    if (ptype && ptype !== 'all') items = items.filter(l => (l.prop_type || '').toLowerCase() === ptype.toLowerCase());
                    if (parsedUrl.searchParams.get('only_pets') === 'true') items = items.filter(l => l.pets_allowed === 1);
                    if (parsedUrl.searchParams.get('only_inspections') === 'true') items = items.filter(l => !!l.inspection_date);
                    if (parsedUrl.searchParams.get('only_favorites') === 'true') items = items.filter(l => !!l.is_favorite);
                    const q = (parsedUrl.searchParams.get('query') || '').toLowerCase().trim();
                    if (q) items = items.filter(l => (l.street || '').toLowerCase().includes(q) || (l.suburb || '').toLowerCase().includes(q) || (l.description || '').toLowerCase().includes(q));
                } catch(err) {}
                return {
                    ok: true,
                    json: async () => ({ count: items.length, listings: items })
                };
            }
            if (url.includes('/api/stats')) {
                const under550 = INITIAL_LISTINGS.filter(l => l.price && l.price <= 550);
                const sum = under550.reduce((acc, c) => acc + c.price, 0);
                return {
                    ok: true,
                    json: async () => ({
                        total_under_550: under550.length,
                        avg_price: Math.round(sum / (under550.length || 1)),
                        min_price: 360,
                        max_price: 550,
                        inspections_count: INITIAL_LISTINGS.filter(l => l.inspection_date).length,
                        pets_count: INITIAL_LISTINGS.filter(l => l.pets_allowed === 1).length,
                        favorites_count: 0,
                        suburbs: [
                            { suburb: 'Sydney', count: 18 },
                            { suburb: 'Melbourne', count: 14 },
                            { suburb: 'Brisbane', count: 10 },
                            { suburb: 'Perth', count: 8 },
                            { suburb: 'Adelaide', count: 6 },
                            { suburb: 'Hobart', count: 4 },
                            { suburb: 'Canberra', count: 4 }
                        ]
                    })
                };
            }
            if (url.includes('/api/portal-links')) {
                return {
                    ok: true,
                    json: async () => ({
                        portals: [
                            { name: "Realestate.com.au", tagline: "Top Australian property portal", category: "Major Portals", url: "https://www.realestate.com.au/rent/in-australia/list-1" },
                            { name: "Domain.com.au", tagline: "Leading national property portal", category: "Major Portals", url: "https://www.domain.com.au/rent/?search=australia" },
                            { name: "Rent.com.au", tagline: "Renter-focused national directory", category: "Major Portals", url: "https://www.rent.com.au/properties/australia" },
                            { name: "Allhomes.com.au", tagline: "Leading portal across ACT & NSW", category: "Major Portals", url: "https://www.allhomes.com.au/rent/" },
                            { name: "Homely.com.au", tagline: "Australian street reviews & rentals", category: "Alternative Portals", url: "https://www.homely.com.au/for-rent/" },
                            { name: "Soho Real Estate", tagline: "Fast property matching & alerts", category: "Alternative Portals", url: "https://soho.com.au/rent" },
                            { name: "Ray White Group", tagline: "Australia's largest real estate network", category: "Local Agencies", url: "https://www.raywhite.com/properties/for-rent" }
                        ]
                    })
                };
            }
            return { ok: true, json: async () => ({ success: true }) };
        }
    };
    """
    
    html = html.replace(
        '<script src="app.js"></script>',
        f'<script>\n{fallback_patch}\n{embedded_js}\n</script>'
    )
    
    out_path = os.path.join(base_dir, "google_sites_embed.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Generated standalone Google Sites embed file: {out_path} ({len(html)} bytes)")

if __name__ == "__main__":
    build_embed()
