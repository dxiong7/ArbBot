import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

# Define a threshold for considering a market dominant (e.g., 91 cents)
DOMINANT_MARKET_THRESHOLD = 91

class KalshiInternalArbitrageFinder:
    """
    Finds arbitrage opportunities within the Kalshi platform itself
    (e.g., binary markets where YES + NO < $1.00).
    """
    def __init__(self, output_file: Optional[str] = None):
        self.output_file = output_file
        self.reset_filtering_stats()

    def reset_filtering_stats(self):
        """Reset statistics related to event filtering."""
        self.total_events_processed = 0
        self.events_with_arbitrage = 0
        self.skipped_events_due_to_no_markets = 0
        self.skipped_events_due_to_no_volume = 0
        self.skipped_events_due_to_dominant_market = 0

    def _write_arbitrage_to_file(self, arbitrage_data: Dict):
        """Append arbitrage opportunity data to the output JSON file."""
        if not self.output_file:
            logger.warning("Output file not specified. Cannot write arbitrage data.")
            return

        # Ensure the directory exists
        output_dir = os.path.dirname(self.output_file)
        if output_dir: # Only create if path is not just a filename
            os.makedirs(output_dir, exist_ok=True)

        # Read existing data or initialize an empty list
        data = []
        if os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0:
            try:
                with open(self.output_file, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, list): # Handle case where file exists but is not a list
                        logger.warning(f"Output file {self.output_file} does not contain a valid JSON list. Initializing.")
                        data = []
            except json.JSONDecodeError:
                logger.warning(f"Output file {self.output_file} is corrupted or empty. Initializing.")
                data = []
            except Exception as e:
                 logger.error(f"Error reading output file {self.output_file}: {e}")
                 data = [] # Default to empty list on error

        # Append new data
        data.append(arbitrage_data)

        # Write back to the file
        try:
            with open(self.output_file, 'w') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Arbitrage opportunity written to {self.output_file}")
        except Exception as e:
            logger.error(f"Error writing to output file {self.output_file}: {e}")


    def _report_binary_arbitrage(self, event: Dict, event_title: str, yes_ask: float, no_ask: float, arbitrage_size: float, total_volume: int, expiry: str, min_sizes: Dict[str, int]):
        """Report a binary event arbitrage opportunity."""
        logger.info(f"Arbitrage opportunity found in event: {event_title}")
        logger.info(f"  Ticker: {event.get('ticker')}")
        logger.info(f"  Strategy: Buy BOTH YES and NO contracts")
        logger.info(f"  YES Ask: {yes_ask:.2f}, NO Ask: {no_ask:.2f}")
        logger.info(f"  Total Cost: {yes_ask + no_ask:.2f}")
        logger.info(f"  Arbitrage Size (Profit per $1): {arbitrage_size:.4f}")
        logger.info(f"  Total Volume: {total_volume}")
        logger.info(f"  Expiry: {expiry}")
        logger.info(f"  Min Sizes (Yes/No): {min_sizes.get('yes', 'N/A')}/{min_sizes.get('no', 'N/A')}")

        arbitrage_data = {
            "type": "binary",
            "platform": "Kalshi",
            "timestamp": datetime.now().isoformat(),
            "event_title": event_title,
            "event_ticker": event.get('ticker'),
            "strategy": "Buy BOTH YES and NO",
            "yes_ask": yes_ask,
            "no_ask": no_ask,
            "arbitrage_size": arbitrage_size,
            "total_volume": total_volume,
            "expiry": expiry,
            "min_sizes": min_sizes
        }
        self._write_arbitrage_to_file(arbitrage_data)
        return True # Indicate arbitrage was found

    def _report_multi_outcome_arbitrage(self, event: Dict, event_title: str, market_details: Dict, total_cost: float, arbitrage_size: float, total_volume: int, expiry: str, min_sizes: Dict[str, int]):
        """Report a multi-outcome event arbitrage opportunity."""
        logger.info(f"Arbitrage opportunity found in event: {event_title}")
        logger.info(f"  Ticker: {event.get('ticker')}")
        logger.info(f"  Strategy: Buy ALL outcomes")
        for ticker, details in market_details.items():
            logger.info(f"    - {ticker}: Ask Price = {details['yes_ask']:.2f}, Size = {details.get('yes_ask_size', 'N/A')}")
        logger.info(f"  Total Cost: {total_cost:.2f}")
        logger.info(f"  Arbitrage Size (Profit per $1): {arbitrage_size:.4f}")
        logger.info(f"  Total Volume: {total_volume}")
        logger.info(f"  Expiry: {expiry}")
        logger.info(f"  Min Sizes: {min_sizes}")

        arbitrage_data = {
            "type": "multi_outcome",
            "platform": "Kalshi",
            "timestamp": datetime.now().isoformat(),
            "event_title": event_title,
            "event_ticker": event.get('ticker'),
            "strategy": "Buy ALL outcomes",
            "market_details": market_details,
            "total_cost": total_cost,
            "arbitrage_size": arbitrage_size,
            "total_volume": total_volume,
            "expiry": expiry,
            "min_sizes": min_sizes
        }
        self._write_arbitrage_to_file(arbitrage_data)
        return True # Indicate arbitrage was found


    def _process_single_outcome_event(self, event: Dict, event_title: str, markets: Dict[str, Dict], expiry: str) -> bool:
        """
        Process a single outcome (binary) event for arbitrage.
        Arbitrage exists if yes_ask + no_ask < 1.00.
        Returns True if arbitrage is found, False otherwise.
        """
        yes_market = markets.get('YES')
        no_market = markets.get('NO')

        if not yes_market or not no_market:
            logger.debug(f"Skipping binary event {event_title}: Missing YES or NO market.")
            # Not counted as skipped due to no markets, as some markets existed initially
            return False

        yes_ask = yes_market.get('yes_ask')
        no_ask = no_market.get('yes_ask') # Note: 'no_ask' is the 'yes_ask' of the NO market
        yes_ask_size = yes_market.get('yes_ask_size', 0)
        no_ask_size = no_market.get('yes_ask_size', 0)
        yes_bid = yes_market.get('yes_bid') # Use bid for dominance check
        no_bid = no_market.get('yes_bid')  # Use bid for dominance check
        yes_volume = yes_market.get('volume', 0)
        no_volume = no_market.get('volume', 0)

        if yes_ask is None or no_ask is None:
            logger.debug(f"Skipping binary event {event_title}: Missing ask price for YES or NO market.")
            return False

        # Check for volume
        total_volume = yes_volume + no_volume
        if total_volume == 0:
            logger.info(f"Skipping event {event_title}: Zero volume in YES/NO markets.")
            self.skipped_events_due_to_no_volume += 1
            return False

        # Check for dominant market (indicative of near-certain outcome)
        if yes_bid is not None and yes_bid >= DOMINANT_MARKET_THRESHOLD:
             logger.info(f"Skipping event {event_title}: YES market bid >= {DOMINANT_MARKET_THRESHOLD}.")
             self.skipped_events_due_to_dominant_market += 1
             return False
        if no_bid is not None and no_bid >= DOMINANT_MARKET_THRESHOLD:
             logger.info(f"Skipping event {event_title}: NO market bid >= {DOMINANT_MARKET_THRESHOLD}.")
             self.skipped_events_due_to_dominant_market += 1
             return False

        total_cost = yes_ask + no_ask
        if total_cost < 1.0:
            arbitrage_size = 1.0 - total_cost
            min_sizes = {'yes': yes_ask_size, 'no': no_ask_size}
            # Check if sizes are non-zero before reporting
            if yes_ask_size > 0 and no_ask_size > 0:
                return self._report_binary_arbitrage(event, event_title, yes_ask, no_ask, arbitrage_size, total_volume, expiry, min_sizes)
            else:
                logger.debug(f"Potential binary arbitrage in {event_title} ignored due to zero ask size.")

        return False

    def _process_multi_outcome_event(self, event: Dict, event_title: str, markets: Dict[str, Dict], expiry: str) -> bool:
        """
        Process a multi-outcome (mutually exclusive) event for arbitrage.
        Arbitrage exists if the sum of ask prices for all outcomes < 1.00.
        Returns True if arbitrage is found, False otherwise.
        """
        total_cost = 0.0
        total_volume = 0
        min_sizes = {}
        market_details = {} # Store details for reporting
        all_asks_available = True
        all_ask_sizes_positive = True

        if not markets: # Should have been caught earlier, but double-check
             return False

        for ticker, market_data in markets.items():
            ask_price = market_data.get('yes_ask')
            ask_size = market_data.get('yes_ask_size', 0)
            volume = market_data.get('volume', 0)
            bid_price = market_data.get('yes_bid') # Use bid for dominance check

            if ask_price is None:
                logger.debug(f"Skipping multi-outcome event {event_title}: Market {ticker} missing ask price.")
                all_asks_available = False
                break # Cannot calculate arbitrage if any outcome is missing price

            # Check for dominant market within the multi-outcome set
            if bid_price is not None and bid_price >= DOMINANT_MARKET_THRESHOLD:
                logger.info(f"Skipping event {event_title}: Outcome {ticker} bid >= {DOMINANT_MARKET_THRESHOLD}.")
                self.skipped_events_due_to_dominant_market += 1
                return False # Skip the whole event if one outcome is dominant

            if ask_size <= 0:
                all_ask_sizes_positive = False
                # Don't break here, calculate total cost anyway for logging/debugging if needed

            total_cost += ask_price
            total_volume += volume
            min_sizes[ticker] = ask_size
            market_details[ticker] = {'yes_ask': ask_price, 'yes_ask_size': ask_size, 'volume': volume, 'yes_bid': bid_price}

        if not all_asks_available:
            return False # Cannot proceed if any ask price was missing

        # Check for volume after processing all markets
        if total_volume == 0:
            logger.info(f"Skipping event {event_title}: Zero total volume across all outcome markets.")
            self.skipped_events_due_to_no_volume += 1
            return False

        if total_cost < 1.0:
            arbitrage_size = 1.0 - total_cost
            # Check if all ask sizes are positive before reporting
            if all_ask_sizes_positive:
                return self._report_multi_outcome_arbitrage(event, event_title, market_details, total_cost, arbitrage_size, total_volume, expiry, min_sizes)
            else:
                logger.debug(f"Potential multi-outcome arbitrage in {event_title} ignored due to zero ask size in one or more outcomes.")

        return False

    def _process_event_markets(self, event: Dict) -> bool:
        """
        Processes a single event's markets fetched from Kalshi API.
        Determines the event type and calls the appropriate processing function.
        Returns True if arbitrage is found, False otherwise.
        Increments skip counters.
        """
        event_title = event.get('title', 'Unknown Event')
        expiry_ts = event.get('expiration_ts')
        expiry = datetime.fromtimestamp(expiry_ts).isoformat() if expiry_ts else 'N/A'
        markets = event.get('markets')

        if not markets:
            logger.info(f"Skipping event {event_title}: No markets found in event data")
            self.skipped_events_due_to_no_markets += 1
            return False

        # Transform list of market dicts into a dict keyed by ticker for easier access
        markets_by_ticker = {m['ticker']: m for m in markets}

        # Determine event type based on market tickers (simple check for YES/NO)
        market_tickers = set(markets_by_ticker.keys())

        is_binary = 'YES' in market_tickers and 'NO' in market_tickers and len(market_tickers) == 2

        arbitrage_found = False
        if is_binary:
            logger.debug(f"Processing binary event: {event_title}")
            arbitrage_found = self._process_single_outcome_event(event, event_title, markets_by_ticker, expiry)
        elif len(markets) > 1:
            # Assuming multi-outcome if more than one market and not strictly YES/NO
            # More robust checking (e.g., using event series_ticker) might be needed
            logger.debug(f"Processing multi-outcome event: {event_title}")
            arbitrage_found = self._process_multi_outcome_event(event, event_title, markets_by_ticker, expiry)
        else:
            logger.debug(f"Skipping event {event_title}: Cannot determine type or only one market.")
            # This case might warrant a different counter if it's common
            return False

        return arbitrage_found


    def find_opportunities(self, events: List[Dict]):
        """
        Main method to find arbitrage opportunities in a list of Kalshi events.
        Processes each event and tracks statistics.
        """
        self.reset_filtering_stats()
        logger.info(f"Processing {len(events)} events for internal Kalshi arbitrage...")

        found_any_arbitrage = False
        for event in events:
            self.total_events_processed += 1
            try:
                if self._process_event_markets(event):
                    self.events_with_arbitrage += 1
                    found_any_arbitrage = True
            except Exception as e:
                event_title = event.get('title', 'Unknown Event')
                logger.error(f"Error processing event {event_title}: {e}", exc_info=True)

        logger.info("Finished processing events.")
        self._display_filtering_stats()

        if not found_any_arbitrage:
            console.print(Panel("No internal Kalshi arbitrage opportunities found in this run.", style="yellow"))


    def _display_filtering_stats(self):
        """Display statistics about event processing and filtering."""
        table = Table(title="Kalshi Internal Arbitrage - Event Filtering Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")

        table.add_row("Total Events Processed", str(self.total_events_processed))
        table.add_row("Events with Arbitrage Found", str(self.events_with_arbitrage))
        table.add_row("Skipped: No Markets", str(self.skipped_events_due_to_no_markets))
        table.add_row("Skipped: Zero Volume", str(self.skipped_events_due_to_no_volume))
        table.add_row(f"Skipped: Dominant Market (Bid >= {DOMINANT_MARKET_THRESHOLD})", str(self.skipped_events_due_to_dominant_market))

        console.print(table)
