import time
import random
from typing import List, Dict, Any
from ingestion.schemas import ArbitrageOpportunity, PaperTrade

class PaperEngine:
    """Simulates paper trading execution and quantifies Detected Edge vs Realized Edge gap."""

    def __init__(self):
        self.trades: List[PaperTrade] = []

    def execute_paper_trade(self, opp: ArbitrageOpportunity) -> PaperTrade:
        """
        Simulates executing a paper trade on a detected arbitrage opportunity.
        Applies a randomized execution latency decay (0.2% to 1.2% slippage drop) to simulate real-world order routing delay.
        """
        t = time.time()
        
        # Simulate execution latency slippage decay
        latency_decay_pct = round(random.uniform(0.15, 0.85), 2)
        
        # Adjust executed prices slightly worse due to latency
        executed_buy = round(opp.avg_buy_price * (1.0 + (latency_decay_pct / 200.0)), 4)
        executed_sell = round(opp.avg_sell_price * (1.0 + (latency_decay_pct / 200.0)), 4)
        
        # Total cost after latency decay
        sets = opp.executable_size
        executed_raw_cost = round((executed_buy + executed_sell) * sets, 2)
        executed_net_cost = round(executed_raw_cost + opp.fee_buy + opp.fee_sell + opp.gas_cost, 2)
        
        realized_profit = round(opp.guaranteed_payout - executed_net_cost, 2)
        realized_roi = round((realized_profit / executed_net_cost) * 100.0, 2) if executed_net_cost > 0 else 0.0
        
        realized_gap = round(opp.net_roi - realized_roi, 2)

        trade = PaperTrade(
            trade_id=f"PAPER-{int(t*1000)}",
            opp_id=opp.opp_id,
            timestamp=t,
            pair_id=opp.pair_id,
            venue_buy=opp.venue_buy,
            venue_sell=opp.venue_sell,
            target_capital=opp.target_capital,
            detected_net_roi=opp.net_roi,
            detected_net_profit=opp.net_profit,
            executed_avg_buy=executed_buy,
            executed_avg_sell=executed_sell,
            executed_net_cost=executed_net_cost,
            simulated_slippage_decay=latency_decay_pct,
            realized_net_profit=realized_profit,
            realized_net_roi=realized_roi,
            realized_gap=realized_gap,
            status="SETTLED_WIN" if realized_profit > 0 else "SETTLED_LOSS",
            notes=f"Paper trade filled across depth. Latency decay: -{latency_decay_pct}%."
        )

        self.trades.append(trade)
        return trade

    def get_summary_analytics(self) -> Dict[str, Any]:
        """Calculates paper trading performance and Detected vs Realized Edge stats"""
        if not self.trades:
            return {
                "total_trades": 0,
                "total_detected_profit": 0.0,
                "total_realized_profit": 0.0,
                "avg_detected_roi": 0.0,
                "avg_realized_roi": 0.0,
                "avg_edge_gap": 0.0,
                "win_rate": 0.0,
                "phantom_arb_ratio": 0.0
            }

        total_trades = len(self.trades)
        total_det_profit = sum(t.detected_net_profit for t in self.trades)
        total_real_profit = sum(t.realized_net_profit for t in self.trades)
        
        avg_det_roi = sum(t.detected_net_roi for t in self.trades) / total_trades
        avg_real_roi = sum(t.realized_net_roi for t in self.trades) / total_trades
        avg_gap = sum(t.realized_gap for t in self.trades) / total_trades

        wins = sum(1 for t in self.trades if t.realized_net_profit > 0)
        win_rate = round((wins / total_trades) * 100.0, 1)

        phantom_arbs = sum(1 for t in self.trades if t.detected_net_roi > 0 and t.realized_net_profit <= 0)
        phantom_arb_ratio = round((phantom_arbs / total_trades) * 100.0, 1)

        return {
            "total_trades": total_trades,
            "total_detected_profit": round(total_det_profit, 2),
            "total_realized_profit": round(total_real_profit, 2),
            "avg_detected_roi": round(avg_det_roi, 2),
            "avg_realized_roi": round(avg_real_roi, 2),
            "avg_edge_gap": round(avg_gap, 2),
            "win_rate": win_rate,
            "phantom_arb_ratio": phantom_arb_ratio
        }
