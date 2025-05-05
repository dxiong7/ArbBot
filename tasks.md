# Arbitrage Bot - Task List

## Core Functionality & Data Aggregation
- [x] Fetch basic market data (bid prices) from Kalshi and Polymarket.
- [x] Implement initial normalization logic.
- [ ] Implement fetching/normalization of **ask prices** (Kalshi: `yes_ask`, `no_ask`; Polymarket: `bestAsk`). *(Partially Done)*
- [ ] Fix Kalshi fetching and calculation of best ask prices (its calculating wrong atm)
- [ ] Filter out markets that are close to resolved (99% or 1%)
- [ ] Refine arbitrage calculation logic in `_find_arbitrage_opportunities` to use ask prices. *(Partially Done)*
- [ ] Extendable interface for adding future market platforms (Myriad, Hedgehog, PredictIt, etc.).
- [ ] Modularize code for better reusability: generic interfaces for fetchers, matchers, notifiers (Separate concerns).

## Market Matching Engine
- [ ] Implement core matching logic combining:
    - [x] **Fuzzy title/question matching** using `thefuzz`.
    - [ ] Fix market matching logic between Polymarket/Kalshi (its checking across markets, but we should check across events)
    - [ ] **Expiration time matching** as a secondary filter.
        - [ ] Parse Kalshi `expiration_time` / `close_time`.
        - [ ] Parse Polymarket `endDate`.
        - [ ] Compare timestamps within a defined tolerance (e.g., same day).
    - [ ] **Semantic similarity matching** using embeddings with 'sentence-transformers' and all-MiniLM-L6-v2
    - [ ] Develop confidence scoring for match candidates.
    - [ ] Explore if we can use **category/tag matching**.
- [ ] Store match candidates in DB

## Arbitrage Detection Engine
- [ ] Implement logic to poll matched market groups (read from DB)
- [ ] Develop core arbitrage calculation (checking if combined prices < 1).
- [ ] (Optional) Factor in fees and liquidity constraints.

## Notifications & Alerts
- [ ] Set up notification system (e.g., Discord, Telegram, or ntfy).
- [ ] Implement alerts for identified arbitrage opportunities, including key details (markets, profit, links).

## Server
- [ ] Deploy app (Render.com background worker, EC2/Docker, Railway.app, Replit Deployments, etc.)
- [ ] Set up Supabase
- [ ] Connect to Supabase db

## Testing & Refinement
- [ ] Testing fuzzy string matching.
- [ ] Add/update unit tests for new normalization logic (ask prices).
- [ ] Add/update unit tests for expiration time matching.
- [ ] Run end-to-end tests to verify arbitrage opportunities identified with ask prices and combined matching.
- [ ] Tune fuzzy matching similarity threshold based on test results.
- [ ] Tune expiration time tolerance based on test results.
- [ ] Develop unit and integration tests for *all* key components (fetching, matching, arbitrage calculation).

## Documentation
- [ ] Update `README.md` with details on the ask price implementation and refined matching strategy.
- [ ] Ensure code comments are clear and up-to-date.

## 🧠 Backlog / Future Features
- [ ] Implement Human-in-the-Loop Verification:
    - [ ] Set up interactive notifier via Discord bot to allow users to verify matching candidates.
    - [ ] Store matched groups in local JSON/DB.
- [ ] Implement notifications via POST requests to NTFY.
