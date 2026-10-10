import time
from typing import List, Dict
from .schemas import Market
from .kalshi_client import KalshiClient
from .polymarket_client import PolymarketClient
from .prophetx_client import ProphetXClient

class FeedOrchestrator:
    """Aggregates all venue clients into a unified realtime feed"""

    def __init__(self):
        self.kalshi = KalshiClient()
        self.polymarket = PolymarketClient()
        self.prophetx = ProphetXClient()
        self.markets_by_venue: Dict[str, List[Market]] = {}
        self.last_update = 0.0

    def poll_all_venues(self) -> List[Market]:
        """Fetches fresh markets across all platforms"""
        all_markets = []
        
        k_mkts = self.kalshi.fetch_public_markets()
        p_mkts = self.polymarket.fetch_public_markets()
        px_mkts = self.prophetx.fetch_public_markets()
        
        self.markets_by_venue["Kalshi"] = k_mkts
        self.markets_by_venue["Polymarket"] = p_mkts
        self.markets_by_venue["ProphetX"] = px_mkts
        
        all_markets.extend(k_mkts)
        all_markets.extend(p_mkts)
        all_markets.extend(px_mkts)
        
        self.last_update = time.time()
        return all_markets

    def get_all_markets(self) -> List[Market]:
        flat = []
        for v, mkts in self.markets_by_venue.items():
            flat.extend(mkts)
        return flat
