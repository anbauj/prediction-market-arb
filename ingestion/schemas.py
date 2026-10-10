import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class OrderBookLevel:
    price: float  # Price per contract (0.0 to 1.0)
    size: float   # Quantity available at this price level

@dataclass
class OrderBook:
    timestamp: float
    venue: str
    market_id: str
    bids: List[OrderBookLevel] = field(default_factory=list)  # Sorted descending by price
    asks: List[OrderBookLevel] = field(default_factory=list)  # Sorted ascending by price

    @property
    def top_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    @property
    def top_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    @property
    def spread(self) -> Optional[float]:
        if self.top_bid is not None and self.top_ask is not None:
            return round(self.top_ask - self.top_bid, 4)
        return None

@dataclass
class Market:
    id: str
    venue: str  # 'Kalshi', 'Polymarket', 'ProphetX'
    title: str
    subtitle: str
    category: str
    expiry_date: str
    expiry_timestamp: float
    resolution_criteria: str
    resolution_source: str
    yes_contract_id: str
    no_contract_id: str
    order_book: OrderBook
    volume_24h: float = 0.0
    url: str = ""

@dataclass
class MatchedPair:
    pair_id: str
    market_a: Market
    market_b: Market
    similarity_score: float  # 0.0 to 100.0
    status: str              # 'PENDING_REVIEW', 'VERIFIED', 'REJECTED'
    risk_flags: List[str]    # e.g., ["DISCREPANT_RESOLUTION_SOURCE", "TIMEZONE_GAP"]
    risk_details: Dict[str, Any]
    match_timestamp: float

@dataclass
class DepthWalkResult:
    target_size: float
    filled_size: float
    average_price: float
    total_cost: float
    slippage: float  # % change from top of book
    levels_walked: int
    fully_executable: bool

@dataclass
class ArbitrageOpportunity:
    opp_id: str
    pair_id: str
    venue_buy: str
    venue_sell: str
    market_buy_title: str
    market_sell_title: str
    buy_outcome: str   # 'YES' or 'NO'
    sell_outcome: str  # 'NO' or 'YES'
    
    top_quoted_buy: float
    top_quoted_sell: float
    naive_spread: float
    
    target_capital: float
    executable_size: float
    avg_buy_price: float
    avg_sell_price: float
    
    raw_cost: float
    fee_buy: float
    fee_sell: float
    gas_cost: float
    total_net_cost: float
    guaranteed_payout: float
    
    net_profit: float
    net_roi: float               # % (e.g. 4.25%)
    annualized_yield: float      # % APR
    days_to_resolution: float
    
    risk_rating: str             # 'LOW', 'MEDIUM', 'HIGH'
    risk_flags: List[str]
    timestamp: float

@dataclass
class PaperTrade:
    trade_id: str
    opp_id: str
    timestamp: float
    pair_id: str
    venue_buy: str
    venue_sell: str
    target_capital: float
    detected_net_roi: float
    detected_net_profit: float
    
    executed_avg_buy: float
    executed_avg_sell: float
    executed_net_cost: float
    simulated_slippage_decay: float  # % loss due to latency execution delay
    realized_net_profit: float
    realized_net_roi: float
    realized_gap: float              # detected_net_roi - realized_net_roi
    status: str                      # 'OPEN', 'SETTLED_WIN', 'SETTLED_LOSS'
    notes: str
