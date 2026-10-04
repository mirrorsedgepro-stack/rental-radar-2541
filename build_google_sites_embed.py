import json
import os
import database

def build_embed():
    database.init_db()
    listings = database.get_listings(max_price=550)
    
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
    // Pre-baked live listings for Google Sites
    const INITIAL_LISTINGS = {listings_json};

    // Override fetchListings for offline/iframe embedding if local API is unreachable
    const originalFetchListings = window.fetchListings;
    """ + js.replace(
        "allListings = data.listings || [];",
        """allListings = (data.listings && data.listings.length > 0) ? data.listings : INITIAL_LISTINGS;
        localStorage.setItem('2541_rentals', JSON.stringify(allListings));"""
    ).replace(
        "let storedListings = [];",
        "let storedListings = JSON.parse(localStorage.getItem('2541_rentals') || 'null') || INITIAL_LISTINGS;"
    ).replace(
        "allListings = [];",
        "allListings = JSON.parse(localStorage.getItem('2541_rentals') || 'null') || INITIAL_LISTINGS;"
    )

    # In case the iframe cannot talk to /api, fallback to INITIAL_LISTINGS
    fallback_patch = """
    // Google Sites Fallback: if fetch fails, use embedded listings
    const origFetch = window.fetch;
    window.fetch = async function(...args) {
        try {
            return await origFetch.apply(this, args);
        } catch(e) {
            console.log("Using embedded 2541 dataset:", args[0]);
            const url = args[0] || '';
            if (url.includes('/api/listings')) {
                return {
                    ok: true,
                    json: async () => ({ count: INITIAL_LISTINGS.length, listings: INITIAL_LISTINGS })
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
                        favorites_count: 0,
                        suburbs: [
                            { suburb: 'Nowra', count: 7 },
                            { suburb: 'Bomaderry', count: 4 },
                            { suburb: 'North Nowra', count: 2 },
                            { suburb: 'West Nowra', count: 2 },
                            { suburb: 'South Nowra', count: 1 }
                        ]
                    })
                };
            }
            if (url.includes('/api/portal-links')) {
                return {
                    ok: true,
                    json: async () => ({
                        portals: [
                            { name: "Realestate.com.au", tagline: "Top Australian rental portal", category: "Major Portals", url: "https://www.realestate.com.au/rent/with-maxPrice-550-in-2541/list-1?activeSort=list-date" },
                            { name: "Domain.com.au", tagline: "Leading property portal", category: "Major Portals", url: "https://www.domain.com.au/rent/?postcode=2541&price=0-550&sort=dateupdated-desc" },
                            { name: "Rent.com.au", tagline: "Renter-focused directory", category: "Major Portals", url: "https://www.rent.com.au/properties/2541?price_max=550" },
                            { name: "Allhomes.com.au", tagline: "Regional NSW listings", category: "Major Portals", url: "https://www.allhomes.com.au/rent/nowra-nsw-2541/?price=0-550" },
                            { name: "Homely.com.au", tagline: "Nowra reviews & rentals", category: "Alternative Portals", url: "https://www.homely.com.au/for-rent/nowra-nsw-2541/properties?price=0-550" },
                            { name: "Gumtree Nowra", tagline: "Private landlord listings", category: "Private & Share", url: "https://www.gumtree.com.au/s-property-for-rent/nowra-2541/c18364l3000947?price=__550" },
                            { name: "Flatmates Nowra", tagline: "Granny flats & studios", category: "Private & Share", url: "https://flatmates.com.au/rent/nowra-2541?max_price=550" },
                            { name: "Ray White Nowra", tagline: "Local agency rentals", category: "Local Agencies", url: "https://raywhiteshoalhavencentralgroup.com.au/properties/residential-for-rent?price_max=550" }
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
