import time
import random
from typing import List
from .schemas import Market, OrderBook, OrderBookLevel

class ProphetXClient:
    """ProphetX / PredictIt Feed Ingestion & Schema Normalizer"""
    
    def __init__(self):
        self.venue_name = "ProphetX"

    def fetch_public_markets(self) -> List[Market]:
        return self.get_simulated_markets()

    def get_simulated_markets(self) -> List[Market]:
        t = time.time()
        template_markets = [
            {
                "id": "PX-FED-CUT-SEP",
                "title": "Federal Reserve Rate Reduction in September 2026",
                "subtitle": "US Central Bank Policy",
                "category": "Economics",
                "resolution": "Resolves YES if FOMC reduces benchmark rate target by >= 25bps at Sept 2026 meeting.",
                "source": "Federal Reserve Board Press Release",
                "expiry_days": 45,
                "base_yes": 0.46
            },
            {
                "id": "PX-STARSHIP-ORBIT",
                "title": "SpaceX Starship Orbital Insertion Accomplished Before Oct 2026",
                "subtitle": "Aerospace",
                "category": "Tech & Science",
                "resolution": "Resolves YES if official broadcast confirms orbital velocity achieved by Starship prior to Oct 1, 2026.",
                "source": "SpaceX Webcast & FAA Telemetry",
                "expiry_days": 35,
                "base_yes": 0.74
            }
        ]
        
        result = []
        for tm in template_markets:
            jitter = random.uniform(-0.01, 0.01)
            yes_p = max(0.05, min(0.95, tm["base_yes"] + jitter))
            
            yes_bid = round(max(0.02, yes_p - 0.01), 2)
            yes_ask = round(min(0.98, yes_p + 0.01), 2)
            
            bids = [
                OrderBookLevel(price=yes_bid, size=random.randint(300, 1000)),
                OrderBookLevel(price=round(max(0.01, yes_bid - 0.02), 2), size=random.randint(800, 2000)),
            ]
            asks = [
                OrderBookLevel(price=yes_ask, size=random.randint(300, 900)),
                OrderBookLevel(price=round(min(0.99, yes_ask + 0.02), 2), size=random.randint(700, 1800)),
            ]
            
            ob = OrderBook(
                timestamp=t,
                venue=self.venue_name,
                market_id=tm["id"],
                bids=bids,
                asks=asks
            )
            
            m = Market(
                id=tm["id"],
                venue=self.venue_name,
                title=tm["title"],
                subtitle=tm["subtitle"],
                category=tm["category"],
                expiry_date="2026-11-15",
                expiry_timestamp=t + 86400 * tm["expiry_days"],
                resolution_criteria=tm["resolution"],
                resolution_source=tm["source"],
                yes_contract_id=f"{tm['id']}-YES",
                no_contract_id=f"{tm['id']}-NO",
                order_book=ob,
                volume_24h=round(random.uniform(20000, 90000), 2),
                url=f"https://prophetx.com/markets/{tm['id'].lower()}"
            )
            result.append(m)
            
        return result
