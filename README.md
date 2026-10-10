# ⚡ Delta-X Arbitrage: Prediction Market Detection Pipeline

> A detection-first multi-venue prediction market arbitrage platform. Monitors live order books (**Kalshi**, **Polymarket**, **ProphetX**), normalizes schemas, matches equivalent contracts with resolution-clause risk assessment, calculates depth-aware net yields after fees and gas, and quantifies **Detected Edge vs Realized Edge** before automated execution is ever unlocked.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13+-emerald.svg)
![Architecture](https://img.shields.io/badge/architecture-5--Stage%20Pipeline-purple.svg)
![Status](https://img.shields.io/badge/status-Production%20Ready-brightgreen.svg)

---

## 🎯 The Core Philosophy: Detection First

Most prediction market arbitrage projects fail because they assume **quoted top-of-book spread = executable spread**. Thin order books mean fill prices move against you, platform taker fees eat small edges, and discrepant resolution wording creates phantom arbitrage that leads to catastrophic losses.

**Delta-X Arbitrage** solves this by enforcing a strict **5-Stage Pipeline**:

```
 ┌─────────────────────────────────────────────────────────┐
 │ Stage 1: Multi-Venue Data Ingestion                     │
 │ Kalshi REST/WS | Polymarket CTF/Gamma | ProphetX Feed   │
 └────────────────────────────┬────────────────────────────┘
                              │ Standardized Market Schema
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Stage 2: Event & Resolution Matcher                     │
 │ Semantic Title Matching + Expiry Alignment + Risk Flags │
 │ Human-in-the-Loop Audit & Verification UI               │
 └────────────────────────────┬────────────────────────────┘
                              │ Approved Matched Pairs
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Stage 3: Depth & Fee-Aware Arbitrage Detector           │
 │ Order Book Depth Walking | Fee Deduction (Gas/Taker)   │
 │ Capital Lockup Yield & Capital Efficiency Calculation   │
 └────────────────────────────┬────────────────────────────┘
                              │ Executable Opportunities
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Stage 4: Alerting & Paper Trading (Validation Layer)    │
 │ Real-time Alerts | Simulated Fills | PnL Tracking       │
 │ Detected vs. Realized Edge Gap Analytics                │
 └────────────────────────────┬────────────────────────────┘
                              │ Long-term Validation Record
                              ▼
 ┌─────────────────────────────────────────────────────────┐
 │ Stage 5: Execution Engine (Protected / Safety Locked)   │
 │ Dry-run Sandbox | Guardrails | Emergency Kill Switch     │
 └────────────────────────────┴────────────────────────────┘
```

---

## ✨ Key Features

- **🌐 Multi-Venue Schema Normalization**: Unified `Market` and `OrderBook` schema across Kalshi, Polymarket CTF, and ProphetX.
- **🧠 Semantic Matcher & Resolution Risk Tagger**: Synonym-aware title matching (maps `Fed` ↔ `Federal Reserve`, `CPI` ↔ `Inflation`) combined with resolution criteria diffing to flag oracle vs. official government source discrepancies.
- **📊 Order Book Depth Walking**: Simulates buying across multiple order book depth levels up to target capital ($100–$10,000) to calculate exact executable fill prices and slippage.
- **💸 Fee & Friction Engine**: Deducts Kalshi taker fees (`~0.07 * price * (1 - price)`), Polymarket Polygon gas fees + bridge friction, and computes annualized yield APR.
- **🗺️ Explicit Trade Action Blueprint**: Generates step-by-step instructions showing exact platform URLs, contract titles, sides (`BUY YES` / `BUY NO`), limit prices, and net outlays.
- **🧪 Edge Realization Lab**: Simulates paper executions with latency decay to track the **Detected Edge vs Realized Edge Gap**.
- **🛡️ Stage 5 Protected Execution Sandbox**: Execution module isolated behind pre-live checklist requirements (5+ paper trades required before unlock), kill switch, and dry-run mode.

---

## 💻 Tech Stack

- **Backend**: Python 3.13 (Multi-threaded HTTP REST API server with zero external package requirements).
- **Frontend**: HTML5, Vanilla CSS3 (Obsidian Glassmorphism Dark Theme), Modern ES6 JavaScript.
- **Testing**: Python `unittest` suite (`tests/test_pipeline.py`).

---

## ⚡ Quickstart & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/prediction-market-arb.git
cd prediction-market-arb
```

### 2. Run the Server
No heavy dependencies or pip installs required! Run directly with Python:

```bash
python server.py
```

### 3. Open the Dashboard
Open your browser and navigate to:
```
http://localhost:8000
```

---

## 🧪 Running Unit Tests

To run the automated pipeline test suite:

```bash
python -m unittest tests/test_pipeline.py
```

All 5 core unit tests validate depth walking math, fee calculator deductions, resolution risk tagging, and paper trading latency decay.

---

## 📂 Repository Structure

```
prediction-market-arb/
├── server.py                     # Multi-threaded HTTP server with REST APIs & static router
├── package.json                  # Project metadata
├── .gitignore                    # Python & Web build exclusions
├── README.md                     # Documentation
├── ingestion/
│   ├── schemas.py                # Core dataclasses (Market, OrderBook, Opportunity)
│   ├── kalshi_client.py          # Kalshi API fetcher & normalizer
│   ├── polymarket_client.py      # Polymarket CTF API fetcher & normalizer
│   ├── prophetx_client.py        # ProphetX / PredictIt normalizer
│   └── feed_orchestrator.py      # Multi-venue polling feed manager
├── matching/
│   ├── event_matcher.py          # Cross-venue title matcher with synonym stemming
│   └── resolution_analyzer.py    # Resolution criteria diffing & risk flags
├── detector/
│   ├── depth_walker.py           # Multi-level order book depth walking algorithm
│   └── fee_calculator.py         # Venue taker fees, gas, slippage & net ROI math
├── paper_trading/
│   └── paper_engine.py           # Simulated trade execution & edge realization gap
├── static/
│   ├── index.html                # Terminal HTML dashboard layout
│   ├── css/styles.css            # Dark obsidian glassmorphism styles
│   └── js/app.js                 # Frontend application & polling controller
└── tests/
    └── test_pipeline.py          # Unit test suite
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/markets` | `GET` | Returns all normalized markets by venue. |
| `/api/matches` | `GET` | Returns matched contract pairs with risk flags & audit statuses. |
| `/api/matches/status` | `POST` | Updates human audit status (`VERIFIED` / `REJECTED`). |
| `/api/opportunities` | `GET` | Returns live depth-walked arbitrage opportunities (`?capital=1000`). |
| `/api/paper/execute` | `POST` | Simulates executing a paper trade against order book depth. |
| `/api/paper/analytics` | `GET` | Returns paper trading history and Detected vs Realized Edge stats. |
| `/api/stage5/status` | `GET` | Returns Stage 5 execution lock state & checklist progress. |

---

## 🔐 Security & Credentials Hygiene

> [!WARNING]
> API keys, private keys, and wallet credentials should **never** be committed to Git repositories. Keep all credentials isolated inside local `.env` files (which are ignored by `.gitignore`).

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
