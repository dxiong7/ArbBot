import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import json
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .kalshi_client import KalshiClient
from .polymarket_client import PolymarketClient
from .market_processor import MarketProcessor
from .arbitrage_detector import ArbitrageDetector
from .config import (
    KALSHI_API_KEY, KALSHI_PRIVATE_KEY, POLYMARKET_API_KEY, POLYMARKET_PRIVATE_KEY,
    CHECK_INTERVAL, SIMILARITY_THRESHOLD, MIN_PROFIT_THRESHOLD,
    LOG_LEVEL, LOG_FILE, INTERNAL_ONLY_MODE, ARBITRAGE_OUTPUT_FILE
)

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console = Console()

class ArbitrageBot:
    def __init__(self):
        self.kalshi_client = KalshiClient(KALSHI_API_KEY, KALSHI_PRIVATE_KEY)
        self.polymarket_client = PolymarketClient(POLYMARKET_PRIVATE_KEY)
        self.logger = logging.getLogger(__name__)

    def run(self):
        self.logger.info("Arbitrage Bot starting...")
        while True:
            try:
                self.logger.info("Fetching data from platforms...")
                # Fetch Kalshi multi-leg exclusive events
                kalshi_events = self.kalshi_client.get_all_multileg_exclusive_events()
                self.logger.info(f"Fetched {len(kalshi_events)} multi-leg exclusive events from Kalshi.")
                
                # Fetch Polymarket events (filtered by expiry)
                polymarket_events = self.polymarket_client.get_events()
                self.logger.info(f"Fetched {len(polymarket_events)} events from Polymarket.")

                # Process data into a comparable format
                processed_kalshi_markets = self._process_kalshi_events(kalshi_events)
                processed_polymarket_markets = self._process_polymarket_events(polymarket_events)
                logger.info(json.dumps(processed_kalshi_markets[0], indent=4)[:500])
                logger.info(json.dumps(processed_polymarket_markets[0], indent=4)[:500])
                # Find arbitrage opportunities
                opportunities = self._find_arbitrage_opportunities(processed_kalshi_markets, processed_polymarket_markets)

                if opportunities:
                    self.logger.info(f"Found {len(opportunities)} potential arbitrage opportunities:")
                    for opp in opportunities:
                        self.logger.info(f" - {opp}")
                else:
                    self.logger.info("No arbitrage opportunities found in this cycle.")

            except Exception as e:
                self.logger.error(f"An error occurred: {e}", exc_info=True)

            self.logger.info("Sleeping for 60 seconds...")
            time.sleep(60)

    def _process_kalshi_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes raw Kalshi event data and normalizes relevant markets.

        Args:
            events: A list of dictionaries, where each dictionary represents
                    a Kalshi event containing a list of markets.

        Returns:
            A list of normalized market dictionaries.
        """
        processed_markets = []
        self.logger.info(f"Processing {len(events)} Kalshi events...")

        for event in events:
            event_title = event.get('title', 'Unknown Event')
            event_ticker = event.get('event_ticker', 'UnknownEventTicker')
            markets_in_event = event.get('markets', [])
            if not markets_in_event:
                self.logger.info(f"No markets found in Kalshi event: {event_ticker}")
                continue

            self.logger.debug(f"Processing {len(markets_in_event)} markets within Kalshi event '{event_title}' ({event_ticker})")

            for market in markets_in_event:
                try:
                    # --- Filtering ---
                    if market.get('status') != 'active':
                        # self.logger.debug(f"Skipping inactive Kalshi market: {market.get('ticker', 'UnknownTicker')}")
                        continue

                    # --- Extraction ---
                    ticker = market.get('ticker')
                    yes_sub_title = market.get('yes_sub_title', '')
                    yes_bid_cents = market.get('yes_bid')
                    no_bid_cents = market.get('no_bid')
                    yes_ask_cents = market.get('yes_ask') # Extract ask price
                    no_ask_cents = market.get('no_ask')   # Extract ask price

                    # --- Validation ---
                    if not ticker:
                        self.logger.warning(f"Skipping Kalshi market in event '{event_title}' due to missing ticker. Market data: {market}")
                        continue
                    if yes_bid_cents is None or no_bid_cents is None:
                        self.logger.info(f"Skipping Kalshi market '{ticker}' due to missing bid prices (yes_bid={yes_bid_cents}, no_bid={no_bid_cents}).")
                        continue
                    if yes_ask_cents is None or no_ask_cents is None: # Validate ask prices
                        self.logger.info(f"Skipping Kalshi market '{ticker}' due to missing ask prices (yes_ask={yes_ask_cents}, no_ask={no_ask_cents}).")
                        continue
                    if not isinstance(yes_bid_cents, (int, float)) or not isinstance(no_bid_cents, (int, float)) \
                       or not isinstance(yes_ask_cents, (int, float)) or not isinstance(no_ask_cents, (int, float)): # Validate types
                        self.logger.warning(f"Skipping Kalshi market '{ticker}' due to non-numeric bid/ask prices (bids: {yes_bid_cents},{no_bid_cents}; asks: {yes_ask_cents},{no_ask_cents}).")
                        continue

                    # --- Normalization ---
                    normalized_title = f"{event_title} - {yes_sub_title}" if yes_sub_title else event_title
                    # Convert cents to probability (0.0 to 1.0)
                    yes_price = float(yes_bid_cents) / 100.0  # Sell Yes price
                    no_price = float(no_bid_cents) / 100.0    # Sell No price
                    yes_ask_price = float(yes_ask_cents) / 100.0 # Buy Yes price
                    no_ask_price = float(no_ask_cents) / 100.0   # Buy No price

                    # --- Appending ---
                    processed_markets.append({
                        'platform': 'Kalshi',
                        'ticker': ticker,
                        'title': normalized_title,
                        'yes_price': yes_price,       # Price to SELL Yes
                        'no_price': no_price,        # Price to SELL No
                        'yes_ask_price': yes_ask_price, # Price to BUY Yes
                        'no_ask_price': no_ask_price,  # Price to BUY No
                        'raw_market': market # Store original market data
                    })
                    # self.logger.debug(f"Successfully processed Kalshi market: {ticker} - {normalized_title}")

                except Exception as e:
                    # Catch errors during individual market processing
                    market_id = market.get('ticker', 'UnknownTicker')
                    self.logger.error(f"Error processing Kalshi market {market_id} from event '{event_title}': {e}", exc_info=False)

        self.logger.info(f"Extracted {len(processed_markets)} processable markets from {len(events)} Kalshi events.")
        return processed_markets

    def _process_polymarket_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes raw Polymarket event data (containing market summaries)
        and normalizes relevant markets.

        Args:
            events: A list of dictionaries, where each dictionary represents
                    a Polymarket event containing a list of market summaries.

        Returns:
            A list of normalized market dictionaries.
        """
        processed_markets = []
        self.logger.info(f"Processing {len(events)} Polymarket events...")

        for event in events:
            event_title = event.get('title', event.get('slug', 'Unknown Event'))
            markets_in_event = event.get('markets', [])
            if not markets_in_event:
                 self.logger.info(f"No markets found in Polymarket event: {event_title}")
                 continue

            #self.logger.debug(f"Processing {len(markets_in_event)} market summaries within Polymarket event '{event_title}'")

            for market_summary in markets_in_event:
                market_id = market_summary.get('id') # Use ID for logging errors if slug is missing
                try:
                    # --- Filtering ---
                    if market_summary.get('closed') or not market_summary.get('active'):
                        # self.logger.debug(f'Skipping market: {market_summary.get("slug", market_id)} due to closed/inactive status')
                        continue

                    # --- Extraction ---
                    ticker = market_summary.get('slug') # Use slug as the primary ticker
                    question = market_summary.get('question', 'Unknown Question') # Use question for title
                    best_bid = market_summary.get('bestBid')
                    best_ask = market_summary.get('bestAsk')

                    # --- Validation ---
                    if not ticker:
                         #self.logger.warning(f"Skipping Polymarket market summary (ID: {market_id}) within event '{event_title}' due to missing 'slug'. Summary: {market_summary}")
                         continue
                    if best_bid is None or best_ask is None:
                        #self.logger.info(f"Skipping Polymarket market '{ticker}' due to missing bestBid or bestAsk (bestBid={best_bid}, bestAsk={best_ask}).")
                        continue
                    if not isinstance(best_bid, (int, float, str)) or not isinstance(best_ask, (int, float, str)):
                        self.logger.warning(f"Skipping Polymarket market '{ticker}' due to non-numeric or unexpected type price data: bestBid={best_bid} ({type(best_bid)}), bestAsk={best_ask} ({type(best_ask)})")
                        continue
                    
                    # Convert string prices safely
                    try:
                        best_bid_float = float(best_bid)
                        best_ask_float = float(best_ask)
                    except (ValueError, TypeError):
                        self.logger.warning(f"Skipping Polymarket market '{ticker}' due to invalid price format: bestBid={best_bid}, bestAsk={best_ask}")
                        continue
                        
                    if not (0.0 <= best_bid_float <= 1.0): # Check valid range for deriving no_ask_price
                         self.logger.warning(f"Skipping Polymarket market '{ticker}' due to invalid bestBid price ({best_bid_float}) for deriving no_ask_price.")
                         continue
                    if not (0.0 <= best_ask_float <= 1.0): # Check valid range for deriving no_price
                         self.logger.warning(f"Skipping Polymarket market '{ticker}' due to invalid bestAsk price ({best_ask_float}) for deriving no_price.")
                         continue

                    # --- Normalization ---
                    # Prices are already in 0.0 to 1.0 format
                    yes_price = best_bid_float       # Sell Yes price (best bid for Yes)
                    yes_ask_price = best_ask_float   # Buy Yes price (best ask for Yes)
                    no_price = 1.0 - best_ask_float  # Sell No price (derived: 1 - best ask for Yes)
                    no_ask_price = 1.0 - best_bid_float # Buy No price (derived: 1 - best bid for Yes)

                    # --- Appending ---
                    processed_markets.append({
                        'platform': 'Polymarket',
                        'ticker': ticker,
                        'title': question, # Use the market question as the title
                        'yes_price': yes_price,         # Price to SELL Yes
                        'no_price': no_price,          # Price to SELL No
                        'yes_ask_price': yes_ask_price,   # Price to BUY Yes
                        'no_ask_price': no_ask_price,    # Price to BUY No
                        'raw_market': market_summary # Store original market summary
                    })
                    # self.logger.debug(f"Successfully processed Polymarket market: {ticker} - {question}")

                except Exception as e:
                    # Catch errors during individual market processing
                    log_id = ticker or market_id # Use slug if available, else ID for logging
                    self.logger.error(f"Error processing Polymarket market {log_id} from event '{event_title}': {e}", exc_info=False)

        self.logger.info(f"Extracted {len(processed_markets)} processable markets from {len(events)} Polymarket events.")
        return processed_markets

    def _find_arbitrage_opportunities(self, kalshi_markets: List[Dict[str, Any]], polymarket_markets: List[Dict[str, Any]]) -> List[str]:
        """Identifies arbitrage opportunities between Kalshi and Polymarket markets."""
        opportunities = []
        self.logger.info(f"Comparing {len(kalshi_markets)} processed Kalshi markets against {len(polymarket_markets)} processed Polymarket markets.")
        
        # Simplified comparison logic (example: matching tickers)
        # TODO: Implement more sophisticated matching (e.g., NLP on questions/titles)
        # TODO: Handle the case where polymarket_markets is empty due to current processing logic
        if not polymarket_markets:
            self.logger.info("Skipping arbitrage check as no processed Polymarket market data is available.")
            return []

        kalshi_map = {market['ticker']: market for market in kalshi_markets}
        
        for polymarket_market in polymarket_markets:
            ticker = polymarket_market.get('ticker')
            if ticker in kalshi_map:
                kalshi_market = kalshi_map[ticker]
                # Example arbitrage logic: Check if buying on one platform and selling on the other is profitable
                # This is a vast simplification and real-world arbitrage involves more complexities
                if kalshi_market['yes_ask_price'] < polymarket_market['yes_price']:
                    opportunities.append(f"Buy YES on Kalshi ({kalshi_market['yes_ask_price']}) and sell on Polymarket ({polymarket_market['yes_price']})")
                elif kalshi_market['no_ask_price'] < polymarket_market['no_price']:
                    opportunities.append(f"Buy NO on Kalshi ({kalshi_market['no_ask_price']}) and sell on Polymarket ({polymarket_market['no_price']})")
        
        return opportunities

if __name__ == "__main__":
    bot = ArbitrageBot()
    bot.run()