import sys
import os
import unittest
import time

# Add root project path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ingestion.schemas import Market, OrderBook, OrderBookLevel, MatchedPair
from detector.depth_walker import DepthWalker
from detector.fee_calculator import FeeCalculator
from matching.resolution_analyzer import ResolutionAnalyzer
from matching.event_matcher import EventMatcher
from paper_trading.paper_engine import PaperEngine

class TestArbitragePipeline(unittest.TestCase):

    def test_depth_walker_exact_math(self):
        """Test order book depth walking for multi-level order fills."""
        asks = [
            OrderBookLevel(price=0.40, size=500),  # Max cost: $200
            OrderBookLevel(price=0.45, size=1000), # Max cost: $450
            OrderBookLevel(price=0.50, size=2000), # Max cost: $1000
        ]
        
        # Test $500 target capital budget
        result = DepthWalker.walk_asks(asks, target_dollar_amount=500.0)
        
        # Level 1: 500 contracts @ 0.40 = $200 (Remaining budget = $300)
        # Level 2: 300 / 0.45 = 666.67 contracts @ 0.45 = $300
        # Total contracts = 1166.67
        # Average price = 500 / 1166.67 = ~0.4286
        self.assertTrue(result.fully_executable)
        self.assertAlmostEqual(result.total_cost, 500.0, delta=0.5)
        self.assertGreater(result.average_price, 0.40)
        self.assertLess(result.average_price, 0.45)
        self.assertEqual(result.levels_walked, 2)

    def test_fee_calculator_and_net_roi(self):
        """Test net ROI after Kalshi taker fees and Polymarket gas fees."""
        # Kalshi fee for 1000 contracts @ 0.40:
        # fee_per_contract = 0.07 * 0.40 * 0.60 = 0.0168 ($16.80)
        kalshi_fee = FeeCalculator.calculate_kalshi_taker_fee(1000, 0.40)
        self.assertAlmostEqual(kalshi_fee, 16.80, delta=0.1)

        # Polymarket fee: 0.1% friction + $0.15 gas
        poly_friction, poly_gas = FeeCalculator.calculate_polymarket_fee(1000, 0.50)
        self.assertEqual(poly_friction, 0.50)
        self.assertEqual(poly_gas, 0.15)

    def test_resolution_analyzer_risk_flags(self):
        """Test detection of resolution source and expiry risk flags."""
        t = time.time()
        m1 = Market(
            id="M1", venue="Kalshi", title="US GDP", subtitle="", category="Econ",
            expiry_date="2026-11-01", expiry_timestamp=t,
            resolution_criteria="Resolves strictly based on BEA initial advance estimate.",
            resolution_source="Bureau of Economic Analysis (BEA)",
            yes_contract_id="M1-Y", no_contract_id="M1-N",
            order_book=OrderBook(t, "Kalshi", "M1")
        )
        
        m2 = Market(
            id="M2", venue="Polymarket", title="US GDP", subtitle="", category="Econ",
            expiry_date="2026-11-03", expiry_timestamp=t + 172800, # 48 hours later
            resolution_criteria="Resolves per UMA oracle consensus AP reports.",
            resolution_source="UMA Oracle & AP News",
            yes_contract_id="M2-Y", no_contract_id="M2-N",
            order_book=OrderBook(t, "Polymarket", "M2")
        )

        flags, details = ResolutionAnalyzer.analyze_pair(m1, m2)
        self.assertTrue(any("HIGH_EXPIRY_DELTA" in f or "EXPIRY" in f for f in flags))
        self.assertTrue(any("ORACLE_VS_GOV_SOURCE_DISCREPANCY" in f for f in flags))

    def test_event_matcher_title_similarity(self):
        """Test fuzzy title matching across venues."""
        t1 = "Federal Reserve Cuts Interest Rates at September 2026 Meeting?"
        t2 = "Will the Fed cut interest rates in September 2026?"
        sim = EventMatcher.calculate_title_similarity(t1, t2)
        self.assertGreaterEqual(sim, 50.0)

    def test_paper_engine_edge_realization_gap(self):
        """Test paper trading execution and detected vs realized edge stats."""
        pe = PaperEngine()
        from ingestion.schemas import ArbitrageOpportunity
        opp = ArbitrageOpportunity(
            opp_id="OPP-1", pair_id="PAIR-1", venue_buy="Kalshi", venue_sell="Polymarket",
            market_buy_title="Fed Cut", market_sell_title="Fed Cut", buy_outcome="YES", sell_outcome="NO",
            top_quoted_buy=0.44, top_quoted_sell=0.50, naive_spread=0.06, target_capital=1000.0,
            executable_size=1000.0, avg_buy_price=0.44, avg_sell_price=0.50, raw_cost=940.0,
            fee_buy=15.0, fee_sell=1.0, gas_cost=0.15, total_net_cost=956.15, guaranteed_payout=1000.0,
            net_profit=43.85, net_roi=4.59, annualized_yield=37.2, days_to_resolution=45.0,
            risk_rating="LOW", risk_flags=["LOW_RISK_MATCH"], timestamp=time.time()
        )

        trade = pe.execute_paper_trade(opp)
        self.assertEqual(trade.status, "SETTLED_WIN")
        self.assertGreater(trade.simulated_slippage_decay, 0.0)
        self.assertGreater(trade.realized_gap, 0.0)
        
        stats = pe.get_summary_analytics()
        self.assertEqual(stats["total_trades"], 1)
        self.assertEqual(stats["win_rate"], 100.0)

if __name__ == '__main__':
    unittest.main()
