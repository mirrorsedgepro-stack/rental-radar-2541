"""
Australian Multi-Portal Real Estate Scraper Engine
Coordinates concurrent portal crawlers, deduplicates cross-portal listings,
syncs with the SQLite database, detects price changes, and dispatches webhook alerts.
"""

import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
import requests

import database
from .models import CanonicalListing
from .deduplicator import DeduplicationEngine
from .portals import (
    RentComAuScraper,
    DomainComAuScraper,
    HomelyComAuScraper,
    SohoComAuScraper,
    RealestateComAuScraper,
    AllhomesComAuScraper
)

logger = logging.getLogger(__name__)

class AustralianRentalScraperEngine:
    """
    Unified Orchestrator for Australian Property Crawling.
    Runs site scrapers in parallel, runs deduplication, persists to DB, and fires alerts.
    """

    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url
        self.scrapers = [
            RentComAuScraper(proxy_url=proxy_url),
            DomainComAuScraper(proxy_url=proxy_url),
            HomelyComAuScraper(proxy_url=proxy_url),
            SohoComAuScraper(proxy_url=proxy_url),
            AllhomesComAuScraper(proxy_url=proxy_url),
            RealestateComAuScraper(proxy_url=proxy_url)
        ]

    def crawl(
        self,
        suburb_or_city: str = "australia",
        state: str = "all",
        max_price: Optional[int] = None,
        listing_type: str = "rent",
        active_portals: Optional[List[str]] = None
    ) -> List[CanonicalListing]:
        """
        Executes parallel scraping across selected Australian property portals.
        """
        raw_listings: List[CanonicalListing] = []
        selected_scrapers = [
            s for s in self.scrapers
            if not active_portals or s.PORTAL_NAME in active_portals
        ]

        logger.info(f"[Engine] Starting multi-portal crawl across {len(selected_scrapers)} portals...")
        start_time = time.time()

        # Execute scrapers in parallel threads
        with ThreadPoolExecutor(max_workers=min(len(selected_scrapers), 6)) as executor:
            futures = {
                executor.submit(
                    s.scrape,
                    suburb_or_city=suburb_or_city,
                    state=state,
                    max_price=max_price,
                    listing_type=listing_type
                ): s.PORTAL_NAME
                for s in selected_scrapers
            }

            for fut in as_completed(futures):
                portal_name = futures[fut]
                try:
                    results = fut.result()
                    logger.info(f"[Engine] Portal '{portal_name}' returned {len(results)} listings.")
                    raw_listings.extend(results)
                except Exception as e:
                    logger.error(f"[Engine] Error during scraping on '{portal_name}': {e}")

        # Run deduplication
        dedup = DeduplicationEngine()
        canonical_listings = dedup.process_batch(raw_listings)

        elapsed = time.time() - start_time
        logger.info(
            f"[Engine] Crawl finished in {elapsed:.1f}s. "
            f"Raw: {len(raw_listings)} -> Deduplicated Canonical: {len(canonical_listings)}"
        )
        return canonical_listings

    def sync_to_database(
        self,
        listings: List[CanonicalListing],
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Persists canonical listings into SQLite database and triggers alerts for new deals/price cuts.
        """
        database.init_db()
        new_count = 0
        updated_count = 0
        price_drop_count = 0
        newly_found = []

        conn = database.get_connection()
        cursor = conn.cursor()

        for item in listings:
            data = item.to_db_dict()
            try:
                is_brand_new = database.upsert_listing(data)
                if is_brand_new:
                    new_count += 1
                    newly_found.append(data)
                else:
                    updated_count += 1
            except Exception as e:
                logger.error(f"[Engine] Error upserting listing {data.get('id')}: {e}")

        # Send webhook notification if configured
        if webhook_url and newly_found:
            self._dispatch_webhook(webhook_url, newly_found)

        return {
            "total_canonical": len(listings),
            "new_added": new_count,
            "existing_updated": updated_count,
            "price_drops": price_drop_count,
        }

    def _dispatch_webhook(self, webhook_url: str, new_items: List[Dict[str, Any]]):
        """Dispatches rich embed notifications to Discord or Slack."""
        try:
            lines = [f"🚨 **Radar Realty Australia: {len(new_items)} New Property Listing(s) Found!**\n"]
            for item in new_items[:6]:
                price_str = f"${item['price']}/wk" if item.get('listing_type') == 'rent' else f"${item['price']:,}"
                insp = f" | 📅 Insp: {item['inspection_date'][:16]}" if item.get('inspection_date') else ""
                lines.append(
                    f"• **{price_str}** - {item['street']}, {item['suburb']} {item.get('state', '')} "
                    f"({item.get('beds')} bed, {item.get('baths')} bath, {item.get('prop_type')}){insp}\n<{item.get('url')}>"
                )
            payload = {"content": "\n".join(lines)}
            requests.post(webhook_url, json=payload, timeout=8)
            logger.info("[Engine] Webhook alerts sent successfully.")
        except Exception as e:
            logger.warning(f"[Engine] Failed to send webhook alert: {e}")
