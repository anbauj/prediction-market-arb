import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import time
from typing import Dict, Any

from ingestion.feed_orchestrator import FeedOrchestrator
from matching.event_matcher import EventMatcher
from detector.fee_calculator import FeeCalculator
from paper_trading.paper_engine import PaperEngine

PORT = 8000
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

# Global Pipeline Services
orchestrator = FeedOrchestrator()
matcher = EventMatcher()
paper_engine = PaperEngine()

stage_5_locked = True
stage_5_dry_run = True

# Initial Data Seed
orchestrator.poll_all_venues()

class PipelineRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            self.handle_api_get(path, urllib.parse.parse_qs(parsed.query))
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else ""
        try:
            data = json.loads(post_body) if post_body else {}
        except Exception as e:
            data = {}

        if path.startswith("/api/"):
            self.handle_api_post(path, data)
        else:
            self.send_error(404, "Not Found")

    def handle_api_get(self, path: str, query: Dict[str, Any]):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if path == "/api/markets":
            markets = orchestrator.get_all_markets()
            resp = [self.market_to_dict(m) for m in markets]
            self.wfile.write(json.dumps({"success": True, "markets": resp}).encode('utf-8'))

        elif path == "/api/matches":
            markets = orchestrator.get_all_markets()
            matched_pairs = matcher.find_matches(markets)
            resp = [self.pair_to_dict(p) for p in matched_pairs]
            self.wfile.write(json.dumps({"success": True, "pairs": resp}).encode('utf-8'))

        elif path == "/api/opportunities":
            target_cap = float(query.get('capital', [1000.0])[0])
            markets = orchestrator.get_all_markets()
            matched_pairs = matcher.find_matches(markets)
            
            opps = []
            for pair in matched_pairs:
                opp = FeeCalculator.evaluate_arbitrage(pair, target_capital=target_cap)
                if opp:
                    opps.append(self.opp_to_dict(opp))
                    
            self.wfile.write(json.dumps({"success": True, "opportunities": opps}).encode('utf-8'))

        elif path == "/api/paper/analytics":
            analytics = paper_engine.get_summary_analytics()
            trades = [self.trade_to_dict(t) for t in paper_engine.trades]
            self.wfile.write(json.dumps({"success": True, "analytics": analytics, "trades": trades}).encode('utf-8'))

        elif path == "/api/stage5/status":
            self.wfile.write(json.dumps({
                "success": True,
                "locked": stage_5_locked,
                "dry_run": stage_5_dry_run,
                "paper_trades_count": len(paper_engine.trades),
                "requirement_met": len(paper_engine.trades) >= 5
            }).encode('utf-8'))

        else:
            self.wfile.write(json.dumps({"error": "Unknown Endpoint"}).encode('utf-8'))

    def handle_api_post(self, path: str, data: Dict[str, Any]):
        global stage_5_locked, stage_5_dry_run

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if path == "/api/matches/status":
            pair_id = data.get("pair_id")
            status = data.get("status")
            if pair_id and status:
                matcher.set_pair_status(pair_id, status)
                self.wfile.write(json.dumps({"success": True, "pair_id": pair_id, "status": status}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"success": False, "message": "Missing pair_id or status"}).encode('utf-8'))

        elif path == "/api/refresh":
            orchestrator.poll_all_venues()
            self.wfile.write(json.dumps({"success": True, "timestamp": time.time()}).encode('utf-8'))

        elif path == "/api/paper/execute":
            opp_dict = data.get("opportunity")
            if opp_dict:
                from ingestion.schemas import ArbitrageOpportunity
                opp = ArbitrageOpportunity(
                    opp_id=opp_dict["opp_id"],
                    pair_id=opp_dict["pair_id"],
                    venue_buy=opp_dict["venue_buy"],
                    venue_sell=opp_dict["venue_sell"],
                    market_buy_title=opp_dict["market_buy_title"],
                    market_sell_title=opp_dict["market_sell_title"],
                    buy_outcome=opp_dict["buy_outcome"],
                    sell_outcome=opp_dict["sell_outcome"],
                    top_quoted_buy=opp_dict["top_quoted_buy"],
                    top_quoted_sell=opp_dict["top_quoted_sell"],
                    naive_spread=opp_dict["naive_spread"],
                    target_capital=opp_dict["target_capital"],
                    executable_size=opp_dict["executable_size"],
                    avg_buy_price=opp_dict["avg_buy_price"],
                    avg_sell_price=opp_dict["avg_sell_price"],
                    raw_cost=opp_dict["raw_cost"],
                    fee_buy=opp_dict["fee_buy"],
                    fee_sell=opp_dict["fee_sell"],
                    gas_cost=opp_dict["gas_cost"],
                    total_net_cost=opp_dict["total_net_cost"],
                    guaranteed_payout=opp_dict["guaranteed_payout"],
                    net_profit=opp_dict["net_profit"],
                    net_roi=opp_dict["net_roi"],
                    annualized_yield=opp_dict["annualized_yield"],
                    days_to_resolution=opp_dict["days_to_resolution"],
                    risk_rating=opp_dict["risk_rating"],
                    risk_flags=opp_dict["risk_flags"],
                    timestamp=opp_dict["timestamp"]
                )
                trade = paper_engine.execute_paper_trade(opp)
                self.wfile.write(json.dumps({"success": True, "trade": self.trade_to_dict(trade)}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"success": False, "message": "Missing opportunity object"}).encode('utf-8'))

        elif path == "/api/stage5/toggle":
            action = data.get("action")
            if action == "UNLOCK" and len(paper_engine.trades) >= 5:
                stage_5_locked = False
            elif action == "LOCK":
                stage_5_locked = True
            elif action == "TOGGLE_DRY_RUN":
                stage_5_dry_run = not stage_5_dry_run

            self.wfile.write(json.dumps({
                "success": True,
                "locked": stage_5_locked,
                "dry_run": stage_5_dry_run
            }).encode('utf-8'))

        else:
            self.wfile.write(json.dumps({"error": "Unknown Endpoint"}).encode('utf-8'))

    def market_to_dict(self, m):
        return {
            "id": m.id,
            "venue": m.venue,
            "title": m.title,
            "subtitle": m.subtitle,
            "category": m.category,
            "expiry_date": m.expiry_date,
            "resolution_criteria": m.resolution_criteria,
            "resolution_source": m.resolution_source,
            "order_book": {
                "top_bid": m.order_book.top_bid,
                "top_ask": m.order_book.top_ask,
                "spread": m.order_book.spread,
                "bids": [{"price": b.price, "size": b.size} for b in m.order_book.bids],
                "asks": [{"price": a.price, "size": a.size} for a in m.order_book.asks]
            },
            "volume_24h": m.volume_24h,
            "url": m.url
        }

    def pair_to_dict(self, p):
        return {
            "pair_id": p.pair_id,
            "market_a": self.market_to_dict(p.market_a),
            "market_b": self.market_to_dict(p.market_b),
            "similarity_score": p.similarity_score,
            "status": p.status,
            "risk_flags": p.risk_flags,
            "risk_details": p.risk_details,
            "match_timestamp": p.match_timestamp
        }

    def opp_to_dict(self, o):
        return {
            "opp_id": o.opp_id,
            "pair_id": o.pair_id,
            "venue_buy": o.venue_buy,
            "venue_sell": o.venue_sell,
            "market_buy_title": o.market_buy_title,
            "market_sell_title": o.market_sell_title,
            "buy_outcome": o.buy_outcome,
            "sell_outcome": o.sell_outcome,
            "top_quoted_buy": o.top_quoted_buy,
            "top_quoted_sell": o.top_quoted_sell,
            "naive_spread": o.naive_spread,
            "target_capital": o.target_capital,
            "executable_size": o.executable_size,
            "avg_buy_price": o.avg_buy_price,
            "avg_sell_price": o.avg_sell_price,
            "raw_cost": o.raw_cost,
            "fee_buy": o.fee_buy,
            "fee_sell": o.fee_sell,
            "gas_cost": o.gas_cost,
            "total_net_cost": o.total_net_cost,
            "guaranteed_payout": o.guaranteed_payout,
            "net_profit": o.net_profit,
            "net_roi": o.net_roi,
            "annualized_yield": o.annualized_yield,
            "days_to_resolution": o.days_to_resolution,
            "risk_rating": o.risk_rating,
            "risk_flags": o.risk_flags,
            "timestamp": o.timestamp
        }

    def trade_to_dict(self, t):
        return {
            "trade_id": t.trade_id,
            "opp_id": t.opp_id,
            "timestamp": t.timestamp,
            "pair_id": t.pair_id,
            "venue_buy": t.venue_buy,
            "venue_sell": t.venue_sell,
            "target_capital": t.target_capital,
            "detected_net_roi": t.detected_net_roi,
            "detected_net_profit": t.detected_net_profit,
            "executed_avg_buy": t.executed_avg_buy,
            "executed_avg_sell": t.executed_avg_sell,
            "executed_net_cost": t.executed_net_cost,
            "simulated_slippage_decay": t.simulated_slippage_decay,
            "realized_net_profit": t.realized_net_profit,
            "realized_net_roi": t.realized_net_roi,
            "realized_gap": t.realized_gap,
            "status": t.status,
            "notes": t.notes
        }

def run_server():
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, 'css'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, 'js'), exist_ok=True)
    
    server_address = ('', PORT)
    httpd = socketserver.TCPServer(server_address, PipelineRequestHandler)
    print(f"[*] Prediction Market Arbitrage Server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")

if __name__ == '__main__':
    run_server()
