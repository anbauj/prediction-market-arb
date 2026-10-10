import time
import math
from typing import Optional, List, Tuple
from ingestion.schemas import Market, MatchedPair, ArbitrageOpportunity
from .depth_walker import DepthWalker

class FeeCalculator:
    """Calculates venue fees, gas, slippage, and net yield for candidate arbitrage opportunities."""

    @staticmethod
    def calculate_kalshi_taker_fee(contracts: float, avg_price: float) -> float:
        """Kalshi taker fee formula: ~0.07 * price * (1 - price) per contract"""
        fee_per_contract = 0.07 * avg_price * (1.0 - avg_price)
        return round(max(0.001, fee_per_contract) * contracts, 2)

    @staticmethod
    def calculate_polymarket_fee(contracts: float, avg_price: float) -> Tuple[float, float]:
        """Polymarket: 0% trade fee, but gas fee ($0.15) + 0.1% bridge/settlement friction"""
        friction = round(0.001 * (contracts * avg_price), 2)
        gas = 0.15  # Polygon gas fee estimate
        return friction, gas

    @staticmethod
    def calculate_prophetx_fee(contracts: float, avg_price: float) -> float:
        """ProphetX: 1.5% taker fee on volume"""
        return round(0.015 * (contracts * avg_price), 2)

    @classmethod
    def get_venue_fee(cls, venue: str, contracts: float, avg_price: float) -> Tuple[float, float]:
        """Returns (trading_fee, gas_fee)"""
        if venue == "Kalshi":
            return cls.calculate_kalshi_taker_fee(contracts, avg_price), 0.0
        elif venue == "Polymarket":
            return cls.calculate_polymarket_fee(contracts, avg_price)
        else:
            return cls.calculate_prophetx_fee(contracts, avg_price), 0.0

    @classmethod
    def evaluate_arbitrage(
        cls,
        pair: MatchedPair,
        target_capital: float = 1000.0,
        require_verified: bool = False
    ) -> Optional[ArbitrageOpportunity]:
        """
        Evaluates whether buying YES on Market A and NO on Market B (or vice-versa) yields a guaranteed net arbitrage profit.
        """
        if require_verified and pair.status != "VERIFIED":
            return None

        m_a = pair.market_a
        m_b = pair.market_b

        # Strategy 1: Buy YES on Venue A, Buy NO on Venue B
        # Contract price of NO = (1 - top_bid of YES) or using NO asks directly
        opp = cls._check_directional_arb(pair, m_a, m_b, target_capital)
        if opp:
            return opp

        # Strategy 2: Buy NO on Venue A, Buy YES on Venue B
        opp_reverse = cls._check_directional_arb(pair, m_b, m_a, target_capital)
        if opp_reverse:
            return opp_reverse

        return None

    @classmethod
    def _check_directional_arb(
        cls,
        pair: MatchedPair,
        m_buy_yes: Market,
        m_buy_no: Market,
        target_capital: float
    ) -> Optional[ArbitrageOpportunity]:
        """
        Simulates:
        1. Buying YES contracts on m_buy_yes
        2. Buying NO contracts on m_buy_no (or synthetic NO via 1 - YES price)
        """
        ob_yes = m_buy_yes.order_book
        ob_no = m_buy_no.order_book

        if not ob_yes.asks or not ob_no.asks:
            return None

        top_yes_ask = ob_yes.top_ask
        top_no_ask = ob_no.top_ask  # In binary markets, NO ask is also equal to (1 - YES bid) if explicit NO isn't listed

        if top_yes_ask is None or top_no_ask is None:
            return None

        naive_spread = round(1.0 - (top_yes_ask + top_no_ask), 4)

        # Split target capital evenly across both legs
        half_capital = target_capital / 2.0

        # Walk order books for executable fill prices
        walk_yes = DepthWalker.walk_asks(ob_yes.asks, half_capital)
        walk_no = DepthWalker.walk_asks(ob_no.asks, half_capital)

        if walk_yes.filled_size == 0 or walk_no.filled_size == 0:
            return None

        # Number of guaranteed sets = min(YES contracts, NO contracts)
        guaranteed_sets = min(walk_yes.filled_size, walk_no.filled_size)
        guaranteed_payout = round(guaranteed_sets * 1.0, 2)  # $1 per resolved set

        # Calculate venue fees
        fee_yes, gas_yes = cls.get_venue_fee(m_buy_yes.venue, walk_yes.filled_size, walk_yes.average_price)
        fee_no, gas_no = cls.get_venue_fee(m_buy_no.venue, walk_no.filled_size, walk_no.average_price)

        total_gas = gas_yes + gas_no
        raw_cost = round(walk_yes.total_cost + walk_no.total_cost, 2)
        total_net_cost = round(raw_cost + fee_yes + fee_no + total_gas, 2)

        net_profit = round(guaranteed_payout - total_net_cost, 2)
        net_roi = round((net_profit / total_net_cost) * 100.0, 2) if total_net_cost > 0 else 0.0

        # Calculate days to resolution & APR
        days_to_expiry = max(1.0, round((m_buy_yes.expiry_timestamp - time.time()) / 86400.0, 1))
        annualized_yield = round(net_roi * (365.0 / days_to_expiry), 1)

        # Arbitrage threshold: Must yield > 0.5% net ROI after all friction
        if net_roi > 0.4:
            # Determine Risk Rating
            if "LOW_RISK_MATCH" in pair.risk_flags and pair.status == "VERIFIED":
                risk_rating = "LOW"
            elif pair.status == "PENDING_REVIEW" or any("DISCREPANCY" in f for f in pair.risk_flags):
                risk_rating = "HIGH"
            else:
                risk_rating = "MEDIUM"

            opp_id = f"ARB-{m_buy_yes.venue}-{m_buy_no.venue}-{int(time.time()*1000)}"

            return ArbitrageOpportunity(
                opp_id=opp_id,
                pair_id=pair.pair_id,
                venue_buy=m_buy_yes.venue,
                venue_sell=m_buy_no.venue,
                market_buy_title=m_buy_yes.title,
                market_sell_title=m_buy_no.title,
                buy_outcome="YES",
                sell_outcome="NO",
                top_quoted_buy=top_yes_ask,
                top_quoted_sell=top_no_ask,
                naive_spread=naive_spread,
                target_capital=target_capital,
                executable_size=guaranteed_sets,
                avg_buy_price=walk_yes.average_price,
                avg_sell_price=walk_no.average_price,
                raw_cost=raw_cost,
                fee_buy=fee_yes,
                fee_sell=fee_no,
                gas_cost=total_gas,
                total_net_cost=total_net_cost,
                guaranteed_payout=guaranteed_payout,
                net_profit=net_profit,
                net_roi=net_roi,
                annualized_yield=annualized_yield,
                days_to_resolution=days_to_expiry,
                risk_rating=risk_rating,
                risk_flags=pair.risk_flags,
                timestamp=time.time()
            )

        return None
