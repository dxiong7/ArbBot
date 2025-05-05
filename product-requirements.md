# 🧾 Product Requirements Document (PRD)

## Problem Statement  
Prediction markets often price events differently across platforms due to liquidity fragmentation and market inefficiencies. There's no unified way to surface arbitrage opportunities across them in real time.

---

## Goals
- Detect and alert on arbitrage opportunities across prediction platforms.
- Normalize market data and match equivalent markets across platforms.
- Enable human verification of matches.
- Provide real-time notifications when profitable arb conditions arise.

---

## Key Features

### ✅ 1. Market Data Aggregation
- Fetch market data from platforms and normalize into a common format:
  - T1: **Polymarket** (ClOB API, Gamma Markets API), **Kalshi** (REST API)
  - T2: **Myriad Markets**, **Hedgehog** (internal POST + parser), **PredictIt** (REST API)
  - T3: Manifold, Insight, etc.


### ✅ 2. Market Matching Engine
- Automatically match equivalent markets using:
  - Fuzzy string matching
  - End-time proximity filtering
  - Semantic similarity via Sentence Transformers
- Output candidate matches with a confidence score

### ✅ 3. Human-In-The-Loop Match Verification
- Push match candidates via Discord/Telegram/ntfy
- Users can confirm/reject matches

### ✅ 4. Arbitrage Detection Engine
- Poll confirmed match groups periodically
- Calculate whether the combined price of all outcomes < 1 (accounting for fees if available)
- Alert user when profitable arb exists with estimated gain and max bet size (based on liquidity if known)

### ✅ 5. Notifications & Alerts
- Support push notifications via:
  - Discord, Telegram, ntfy
- Include details like:
  - Matching markets
  - Time remaining
  - Max profit
  - Confidence of match
  - links to markets

---

## Tech Stack (subject to change)
- Python 
- `requests`, `asyncio`, `sentence-transformers`, `fuzzywuzzy`, `APScheduler`
- SQLite or JSON flat-file for persistence
- Discord/Telegram Bots (via `discord.py` or `python-telegram-bot`)
- Optional: FastAPI stubbed for future dashboard

---

## Future Roadmap
- ✅ Add support for more platforms (Manifold, Insight, Augur)
- 🧠 Learn from confirmed matches to auto-tune thresholds
- ⚙️ Add slippage/liquidity modeling
- 💸 Optional: monetization via alerts SaaS or execution tooling