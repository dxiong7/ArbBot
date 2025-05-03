import logging
import time
import traceback
import json
import os
from typing import List, Dict
from datetime import datetime, timezone
import pandas as pd
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
from .kalshi_internal_arb import KalshiInternalArbitrageFinder

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

ARBITRAGE_THRESHOLD = 0.1

class ArbitrageBot:
    def __init__(self):
        try:
            logger.info("Initializing Kalshi client...")
            self.kalshi_client = KalshiClient(KALSHI_API_KEY, KALSHI_PRIVATE_KEY)
            logger.info("Successfully initialized Kalshi client")
        except Exception as e:
            logger.error(f"Failed to initialize Kalshi client: {e}")
            raise

        try:
            logger.info("Initializing Polymarket client with API key: %s", POLYMARKET_PRIVATE_KEY)
            self.polymarket_client = PolymarketClient(POLYMARKET_PRIVATE_KEY)
            logger.info("Successfully initialized Polymarket client")
        except Exception as e:
            logger.error(f"Failed to initialize Polymarket client: {e}")
            raise

        try:
            logger.info("Initializing market processor...")
            self.market_processor = MarketProcessor()
            logger.info("Successfully initialized market processor")
        except Exception as e:
            logger.error(f"Failed to initialize market processor: {e}")
            raise

        try:
            logger.info("Initializing arbitrage detector...")
            self.arbitrage_detector = ArbitrageDetector(similarity_threshold=SIMILARITY_THRESHOLD)
            logger.info("Successfully initialized arbitrage detector")
        except Exception as e:
            logger.error(f"Failed to initialize arbitrage detector: {e}")
            raise
            
        # Initialize event filtering statistics
        self.reset_filtering_stats()
        
        # Instantiate the internal finder
        self.internal_arb_finder = KalshiInternalArbitrageFinder(output_file=ARBITRAGE_OUTPUT_FILE)

    def fetch_market_data(self) -> pd.DataFrame:
        """Fetch and process market data from both platforms as lists of dicts."""
        try:
            # Fetch markets from both platforms (both should return a list of dicts)
            kalshi_markets = self.kalshi_client.get_markets()
            print(f'Got total of {len(kalshi_markets)} markets from Kalshi')
            print('Sample Kalshi market: ', kalshi_markets[0])
            print()
            polymarket_markets, _ = self.polymarket_client.get_markets(active_only=True)
            # If PolymarketClient.get_markets still returns a tuple, extract only the list
            if isinstance(polymarket_markets, tuple):
                polymarket_markets = polymarket_markets[0]
            print(f'Got total of {len(polymarket_markets)} markets from Polymarket')
            print('Sample Polymarket market: ', polymarket_markets[0])
            print()
            
            # Process and normalize the data
            print('Normalizing markets...')
            return self.market_processor.normalize_markets(
                kalshi_markets,
                polymarket_markets
            )
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            raise
            
    def display_opportunities(self, opportunities: List[Dict]) -> None:
        """Display arbitrage opportunities in a formatted table."""
        if not opportunities:
            console.print(Panel("No arbitrage opportunities found.", style="red"))
            return
            
        table = Table(title="Arbitrage Opportunities")
        
        # Add columns
        table.add_column("Kalshi Market", style="cyan")
        table.add_column("Kalshi Price", style="green")
        table.add_column("Polymarket Market", style="cyan")
        table.add_column("Polymarket Price", style="green")
        table.add_column("Profit", style="yellow")
        table.add_column("Strategy", style="magenta")
        
        # Add rows
        for opp in opportunities:
            if opp['max_profit'] >= MIN_PROFIT_THRESHOLD:
                table.add_row(
                    opp['kalshi_title'],
                    f"{opp['kalshi_yes_price']:.3f}/{opp['kalshi_no_price']:.3f}",
                    opp['polymarket_title'],
                    f"{opp['polymarket_yes_price']:.3f}/{opp['polymarket_no_price']:.3f}",
                    f"{opp['max_profit']:.3f}",
                    opp['strategy']
                )
                
        console.print(table)
        
    def check_kalshi_market_arbitrage(self, market):
        """Check a single Kalshi market for arbitrage. Returns dict with info if found, else None."""
        print(f'Checking market: {market}')
        market_id = market.get('id') or market.get('ticker')
        title = market.get('title') or market.get('name') or market.get('ticker')
        expiry = market.get('expiration') or market.get('end_date') or market.get('expiry')
        volume = market.get('volume', 'N/A')
        print(f'Checking market: {title} (ID: {market_id})')
        print(f'  Expiry: {expiry}')
        print(f'  Volume: {volume}')
        print()
        try:
            orderbook = self.kalshi_client.get_market_orderbook(market_id)
            print(f'  Orderbook: {orderbook}')
            print()
            outcomes = orderbook.get('orderbook', {}).get('outcomes', [])
            ask_sum = 0.0
            ask_prices = {}
            min_sizes = {}
            for outcome in outcomes:
                best_ask = outcome.get('best_ask')
                min_size = outcome.get('min_size')
                name = outcome.get('name')
                if best_ask is not None:
                    ask_sum += float(best_ask)
                    ask_prices[name] = float(best_ask)
                    min_sizes[name] = min_size
            if ask_prices and ask_sum < 1.0:
                arbitrage_size = 1.0 - ask_sum
                return {
                    'market_id': market_id,
                    'title': title,
                    'ask_prices': ask_prices,
                    'arbitrage_size': arbitrage_size,
                    'volume': volume,
                    'expiry': expiry,
                    'min_sizes': min_sizes
                }
        except Exception as e:
            logger.error(f"Failed to get orderbook for market {market_id}: {e}")
        return None

    def _write_arbitrage_to_file(self, arbitrage_data):
        """Write arbitrage opportunity data to the output file."""
        try:
            # Add timestamp and formatted date to the data
            now = datetime.now(timezone.utc)
            timestamp = now.isoformat()
            formatted_date = now.strftime("%Y-%m-%d %H:%M:%S UTC")
            arbitrage_data['timestamp'] = timestamp
            arbitrage_data['formatted_date'] = formatted_date
            
            # Calculate expected profit if trade is executed
            arbitrage_size = arbitrage_data.get('arbitrage_size', 0)
            # Assuming a standard trade size of $100
            standard_trade_size = 100
            expected_profit = arbitrage_size * standard_trade_size
            arbitrage_data['expected_profit_usd'] = round(expected_profit, 2)
            
            # Load existing data if file exists
            existing_data = []
            if os.path.exists(ARBITRAGE_OUTPUT_FILE):
                try:
                    with open(ARBITRAGE_OUTPUT_FILE, 'r') as f:
                        existing_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse existing data in {ARBITRAGE_OUTPUT_FILE}, starting fresh")
            
            # Check if this is a duplicate of a recent arbitrage (same event, similar size)
            is_duplicate = False
            for existing in existing_data:
                if (existing.get('event_ticker') == arbitrage_data.get('event_ticker') and
                    existing.get('type') == arbitrage_data.get('type') and
                    abs(existing.get('arbitrage_size', 0) - arbitrage_size) < 0.01):
                    # Check if it was recorded within the last hour
                    if existing.get('timestamp'):
                        existing_time = datetime.fromisoformat(existing.get('timestamp'))
                        time_diff = now - existing_time
                        if time_diff.total_seconds() < 3600:  # 1 hour
                            is_duplicate = True
                            break
            
            if not is_duplicate:
                # Append new data and write back to file
                existing_data.append(arbitrage_data)
                with open(ARBITRAGE_OUTPUT_FILE, 'w') as f:
                    json.dump(existing_data, f, indent=2)
                    
                console.print(f"[bold green]Arbitrage opportunity written to {ARBITRAGE_OUTPUT_FILE}[/bold green]")
                logger.info(f"Arbitrage opportunity written to {ARBITRAGE_OUTPUT_FILE}")
            else:
                logger.info(f"Skipping duplicate arbitrage opportunity for {arbitrage_data.get('event_title')}")
        except Exception as e:
            logger.error(f"Failed to write arbitrage to file: {e}")
    
    # Helper functions for run_internal_only_mode
    def _get_kalshi_event_metadata(self, event):
        """Extract and return event metadata."""
        event_title = event.get('title') or event.get('name') or event.get('ticker')
        expiry = event.get('expiration') or event.get('end_date') or event.get('expiry')
        markets = event.get('markets', [])
        return event_title, expiry, markets

        
    def _should_skip_market(self, market, curr_time):
        """Determine if a market should be skipped based on its properties."""
        market_id = market.get('ticker')
        if not market_id:
            return True, market_id, 0
            
        market_result = market.get('result')
        market_close_time = market.get('close_time')
        if market_result or market_close_time < curr_time:
            logger.info(f"Skipping market {market_id}: Already resolved or closed")
            return True, market_id, 0
            
        # Track volume
        volume = market.get('volume', 0) or 0
        return False, market_id, volume
        
    def _process_orderbook(self, market_id, orderbook):
        """Process orderbook data and extract bid/ask information."""
        if not orderbook:
            logger.error(f"Failed to get orderbook for market {market_id}")
            return None, None, None, False
            
        orderbook_data = orderbook.get('orderbook', {})
        yes_orders = orderbook_data.get('yes', [])
        no_orders = orderbook_data.get('no', [])
        highest_yes_bid = None
        highest_no_bid = None
        min_sizes = {}
        has_bids = False
        
        # Process YES orders
        if yes_orders and len(yes_orders) > 0:
            # Get highest bid (last element)
            best_yes_order = yes_orders[-1]
            highest_yes_bid = float(best_yes_order[0]) / 100.0  # Convert cents to dollars
            min_sizes[f"{market_id}-YES"] = best_yes_order[1]
            has_bids = True
            
        # Process NO orders
        if no_orders and len(no_orders) > 0:
            # Get highest bid (last element)
            best_no_order = no_orders[-1]
            highest_no_bid = float(best_no_order[0]) / 100.0  # Convert cents to dollars
            min_sizes[f"{market_id}-NO"] = best_no_order[1]
            has_bids = True
            
        return highest_yes_bid, highest_no_bid, min_sizes, has_bids
        
    def _calculate_ask_prices(self, market_id, highest_yes_bid, highest_no_bid, yes_prices, no_prices, all_outcomes):
        """Calculate ask prices based on bid prices."""
        yes_best_ask_price = None
        no_best_ask_price = None
        
        # YES ask = 1 - NO bid (if NO bid exists)
        if highest_no_bid is not None:
            yes_best_ask_price = 1.0 - highest_no_bid
            yes_prices[market_id] = yes_best_ask_price
            all_outcomes.append(f"{market_id}-YES")
            
        # NO ask = 1 - YES bid (if YES bid exists)
        if highest_yes_bid is not None:
            no_best_ask_price = 1.0 - highest_yes_bid
            no_prices[market_id] = no_best_ask_price
            all_outcomes.append(f"{market_id}-NO")
            
        return yes_best_ask_price, no_best_ask_price
        
    def _process_single_outcome_event(self, event, event_title, yes_prices, no_prices, min_sizes, total_volume, expiry, highest_yes_bid, highest_no_bid):
        """Process a single outcome event (binary event) for arbitrage opportunities."""
        if highest_yes_bid is None or highest_no_bid is None:
            logger.info(f"  Missing YES or NO orders for single outcome event")
            return False
            
        # Get the single YES and NO market IDs
        yes_market_id = list(yes_prices.keys())[0]
        no_market_id = list(no_prices.keys())[0]
        
        # Get their ask prices
        yes_ask = yes_prices[yes_market_id]
        no_ask = no_prices[no_market_id]
        
        # Calculate total cost to buy both YES and NO
        total_cost = yes_ask + no_ask
        logger.info(f" {event_title}: Binary event detected. Total cost for YES+NO: {total_cost:.4f}")
        
        if total_cost < 1.0:
            arbitrage_size = 1.0 - total_cost
            if arbitrage_size <= ARBITRAGE_THRESHOLD:
                console.print(Panel(f"Arbitrage size {arbitrage_size:.4f} is below threshold {ARBITRAGE_THRESHOLD:.4f} for event {event_title}, Skipping.. ", style="bold yellow"))
                logger.info(f"Arbitrage size {arbitrage_size:.4f} is below threshold {ARBITRAGE_THRESHOLD:.4f} for event {event_title}, Skipping.. ")
                return False
                
            self._report_binary_arbitrage(event, event_title, yes_ask, no_ask, arbitrage_size, total_volume, expiry, min_sizes)
            return True
        else:
            logger.info(f"No arb found for single outcome event {event_title}")
            return False
            
    def _report_binary_arbitrage(self, event, event_title, yes_ask, no_ask, arbitrage_size, total_volume, expiry, min_sizes):
        """Report a binary event arbitrage opportunity."""
        console.print(Panel(f"[ARBITRAGE FOUND] Binary Event: {event_title} (Event Ticker: {event.get('ticker')})\nStrategy: Buy BOTH YES and NO", style="bold green"))
        logger.info(f"  Strategy: Buy both YES ({yes_ask:.4f}) and NO ({no_ask:.4f})")
        logger.info(f"  Arbitrage Size: {arbitrage_size:.4f}")
        logger.info(f"  Total Volume: {total_volume}")
        logger.info(f"  Expiry: {expiry}")
        logger.info(f"  Min Sizes: {min_sizes}")
        
        # Write to output file
        arbitrage_data = {
            "type": "binary",
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
        
    def _process_multi_outcome_event(self, event, event_title, yes_prices, no_prices, yes_sum, no_sum, min_sizes, total_volume, expiry):
        """Process a multi-outcome event for arbitrage opportunities."""
        # For multi-outcome events:
        # An arbitrage exists if either:
        # 1. Sum of all YES prices < 1.0 (can buy all YES outcomes for less than $1)
        # 2. Sum of all NO prices < 1.0 (can buy all NO outcomes for less than $1)
        
        # Check YES side arbitrage
        if yes_prices and yes_sum < 1.0:
            logger.info('Checking for possible arb')
            arbitrage_size = 1.0 - yes_sum
            logger.info(f" {event_title}: Sum of all best YES prices is {yes_sum:.4f}; Volume: {total_volume}")
            if arbitrage_size <= ARBITRAGE_THRESHOLD:
                logger.info(f" {event_title} has Arbitrage size {arbitrage_size:.4f} below threshold of {ARBITRAGE_THRESHOLD:.4f}, Skipping.. ")
                return False
                
            self._report_yes_arbitrage(event, event_title, yes_prices, arbitrage_size, total_volume, expiry, min_sizes)
            return True
            
        # We don't need to check for NO side arbitrage since this isn't possible for multi-outcome events, one outcome must resolve to yes
        # elif no_prices and no_sum < 1.0:
        #     logger.info('Checking for possible arb')
        #     arbitrage_size = 1.0 - no_sum
        #     if arbitrage_size <= ARBITRAGE_THRESHOLD:
        #         logger.info(f"Arbitrage size {arbitrage_size:.4f} is below threshold {ARBITRAGE_THRESHOLD:.4f} for event {event_title}, Skipping.. ")
        #         return False
        #         
        #     self._report_no_arbitrage(event, event_title, no_prices, arbitrage_size, total_volume, expiry, min_sizes)
        #     return True
            
        else:
            logger.info(f"No arb found for event {event_title}")
            return False
            
    def _report_yes_arbitrage(self, event, event_title, yes_prices, arbitrage_size, total_volume, expiry, min_sizes):
        """Report a YES-side arbitrage opportunity."""
        console.print(Panel(f"[ARBITRAGE FOUND] Event: {event_title} (Event Ticker: {event.get('event_ticker')})\nStrategy: Buy ALL YES outcomes", style="bold green"))
        logger.info(f"  Strategy: Buy ALL YES outcomes")
        logger.info(f"  YES Prices: {yes_prices}")
        logger.info(f"  Arbitrage Size: {arbitrage_size:.4f}")
        logger.info(f"  Total Volume: {total_volume}")
        logger.info(f"  Expiry: {expiry}")
        logger.info(f"  Min Sizes: {min_sizes}")
        
        # Write to output file
        arbitrage_data = {
            "type": "multi_outcome_yes",
            "event_title": event_title,
            "event_ticker": event.get('event_ticker'),
            "strategy": "Buy ALL YES outcomes",
            "yes_prices": yes_prices,
            "arbitrage_size": arbitrage_size,
            "total_volume": total_volume,
            "expiry": expiry,
            "min_sizes": min_sizes
        }
        self._write_arbitrage_to_file(arbitrage_data)
        
    def _report_no_arbitrage(self, event, event_title, no_prices, arbitrage_size, total_volume, expiry, min_sizes):
        """Report a NO-side arbitrage opportunity."""
        console.print(Panel(f"[ARBITRAGE FOUND] Event: {event_title} (Event Ticker: {event.get('event_ticker')})\nStrategy: Buy ALL NO outcomes", style="bold green"))
        logger.info(f"  Strategy: Buy ALL NO outcomes")
        logger.info(f"  NO Prices: {no_prices}")
        logger.info(f"  Arbitrage Size: {arbitrage_size:.4f}")
        logger.info(f"  Total Volume: {total_volume}")
        logger.info(f"  Expiry: {expiry}")
        logger.info(f"  Min Sizes: {min_sizes}")
        
        # Write to output file
        arbitrage_data = {
            "type": "multi_outcome_no",
            "event_title": event_title,
            "event_ticker": event.get('event_ticker'),
            "strategy": "Buy ALL NO outcomes",
            "no_prices": no_prices,
            "arbitrage_size": arbitrage_size,
            "total_volume": total_volume,
            "expiry": expiry,
            "min_sizes": min_sizes
        }
        self._write_arbitrage_to_file(arbitrage_data)
        
    def reset_filtering_stats(self):
        """Reset the event filtering statistics counters."""
        self.total_events_processed = 0
        self.events_with_arbitrage = 0
        self.skipped_events_due_to_no_markets = 0
        self.skipped_events_due_to_volume = 0
        self.skipped_events_due_to_dominant_market = 0
        
    def _process_event_markets(self, event, curr_time):
        """Process all markets in an event and check for arbitrage opportunities."""
        event_title, expiry, markets = self._get_kalshi_event_metadata(event)
        self.total_events_processed += 1
        
        # Skip if no markets
        if not markets:
            logger.info(f"Skipping event {event_title}: No markets found")
            self.skipped_events_due_to_no_markets += 1
            return False
            
        # Skip if volume for all markets is 0
        if all(market.get('volume', 0) == 0 for market in markets):
            logger.info(f"Skipping event {event_title}: No volume found")
            self.skipped_events_due_to_volume += 1
            return False
        
        # Skip if any market has a very high yes_bid
        if any(market.get('yes_bid', 0) >= 0.91 for market in markets):
            logger.info(f"Skipping event {event_title}: Dominant market with >=91% yes_bid detected")
            self.skipped_events_due_to_dominant_market += 1
            return False
            
        print(f"Processing event: {event_title}")
        
        # Initialize data structures
        yes_sum = 0.0
        no_sum = 0.0
        yes_prices = {}
        no_prices = {}
        min_sizes = {}
        all_outcomes = []
        total_volume = 0.0
        markets_with_bids = 0
        
        # Process each market in the event
        for market in markets:
            skip_market, market_id, volume = self._should_skip_market(market, curr_time)
            if skip_market:
                continue
                
            # Add to total volume
            total_volume += volume
            
            try:
                # Get and process orderbook
                orderbook = self.kalshi_client.get_market_orderbook(market_id)
                highest_yes_bid, highest_no_bid, market_min_sizes, has_bids = self._process_orderbook(market_id, orderbook)
                if market['ticker'] == 'KXTOPSONG-25MAY10-LUT':
                    print(f"Market: {market['ticker']}")
                    print(f"orderbook: {orderbook}")
                # Update min sizes
                if market_min_sizes:
                    min_sizes.update(market_min_sizes)
                
                # Count markets with bids
                if has_bids:
                    markets_with_bids += 1
                
                # Calculate and store ask prices
                yes_price, no_price = self._calculate_ask_prices(
                    market_id, highest_yes_bid, highest_no_bid, 
                    yes_prices, no_prices, all_outcomes
                )
                
                # Update sums
                if yes_price is not None:
                    yes_sum += yes_price
                if no_price is not None:
                    no_sum += no_price
                    
            except Exception as e:
                logger.error(f"Failed to get orderbook/details for market {market_id}: {e}")
        
        # Only process event if we have at least 2 markets with bids
        if markets_with_bids < 2:
            logger.info(f"Skipping event {event_title}: Only {markets_with_bids} markets have bids")
            return False
            
        logger.info(f"Processing event {event_title} with {len(all_outcomes)} outcomes ({markets_with_bids} markets with bids)")
        logger.info(f"  YES Prices: {yes_prices} (Sum of all YES: {yes_sum:.4f})")
        logger.info(f"  NO Prices: {no_prices} (Sum of all NO: {no_sum:.4f})")
        
        # Check for arbitrage based on event type
        is_single_outcome = len(markets) == 1
        if is_single_outcome:
            return self._process_single_outcome_event(
                event, event_title, yes_prices, no_prices, min_sizes,
                total_volume, expiry, highest_yes_bid, highest_no_bid
            )
        else:
            return self._process_multi_outcome_event(
                event, event_title, yes_prices, no_prices, 
                yes_sum, no_sum, min_sizes, total_volume, expiry
            )
    
    def _summarize_arbitrage_opportunities(self):
        """Summarize all arbitrage opportunities found so far."""
        console.log("Summarizing arbitrage opportunities and reading data in file: ", ARBITRAGE_OUTPUT_FILE)
        if not os.path.exists(ARBITRAGE_OUTPUT_FILE):
            console.print(f"File {ARBITRAGE_OUTPUT_FILE} does not exist.")
            console.print("[yellow]No arbitrage opportunities recorded yet.[/yellow]")
            return
            
        try:
            with open(ARBITRAGE_OUTPUT_FILE, 'r') as f:
                data = json.load(f)
                
            if not data:
                console.print("[yellow]No arbitrage opportunities recorded yet.[/yellow]")
                return
                
            # Sort by timestamp descending
            sorted_data = sorted(data, key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Create a summary table
            table = Table(title=f"Arbitrage Opportunities Summary (Total: {len(data)})")
            table.add_column("Date", style="cyan")
            table.add_column("Event", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Size", style="magenta")
            table.add_column("Profit ($100)", style="red")
            
            # Add the most recent 10 opportunities
            for arb in sorted_data[:10]:
                date = arb.get('formatted_date', 'Unknown')
                event = arb.get('event_title', 'Unknown')
                arb_type = arb.get('type', 'Unknown')
                size = f"{arb.get('arbitrage_size', 0):.4f}"
                profit = f"${arb.get('expected_profit_usd', 0):.2f}"
                table.add_row(date, event, arb_type, size, profit)
                
            console.print(table)
            
            # Calculate some statistics
            total_profit = sum(arb.get('expected_profit_usd', 0) for arb in data)
            avg_size = sum(arb.get('arbitrage_size', 0) for arb in data) / len(data) if data else 0
            
            stats_panel = Panel(
                f"Total Expected Profit: ${total_profit:.2f}\n" +
                f"Average Arbitrage Size: {avg_size:.4f}\n" +
                f"Total Opportunities: {len(data)}",
                title="Statistics",
                style="bold green"
            )
            console.print(stats_panel)
            
        except Exception as e:
            logger.error(f"Error summarizing arbitrage opportunities: {e}")
    
    def run_internal_only_mode(self):
        """Internal-only mode: Only search for arbitrage on Kalshi, starting from events."""
        console.print(Panel("Starting Kalshi Internal-Only Arbitrage Mode (events-based)...", style="bold blue"))
        curr_time = (datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Summarize existing arbitrage opportunities
        self._summarize_arbitrage_opportunities()
        
        while True:
            try:
                logger.info("Fetching Kalshi events for internal analysis...")
                # Use the original method as requested
                events = self.kalshi_client.get_all_multileg_exclusive_events()
                logger.info(f"Fetched {len(events)} suitable Kalshi events.")

                if not events:
                    logger.warning("No suitable open events found from Kalshi.")
                else:
                    # Delegate processing to the specialized finder
                    self.internal_arb_finder.find_opportunities(events)

            except KeyboardInterrupt: # Restore KeyboardInterrupt handling
                console.print(Panel("Shutting down Kalshi Internal-Only Mode...", style="bold red"))
                break
            except Exception as e:
                logger.error(f"An error occurred in the main loop: {e}", exc_info=True)
                console.print(Panel(f"An error occurred: {e}. Check logs.", style="bold red"))
                # Decide if we should break or continue on other errors
                # For now, let's break on general errors too, like KeyboardInterrupt
                break

            # Original logic didn't explicitly support 'continuous' flag here, it ran once or until error/interrupt.
            logger.info("Internal analysis run complete.") # Adjusted message
            break # Exit after one successful pass or error

    def run(self) -> None:
        """Main application loop."""
        if INTERNAL_ONLY_MODE:
            logger.info("Starting Kalshi Internal-Only Mode...")
            try:
                self.run_internal_only_mode()
            except Exception as e:
                logger.error(f"Error in Kalshi Internal-Only Mode: {e}")
                console.print(Panel(f"Error in Kalshi Internal-Only Mode: {e}", style="bold red"))
                raise e
            else:
                logger.info("Kalshi Internal-Only Mode completed successfully.")
                return
        else:
            console.print(Panel("Starting Arbitrage Bot...", style="bold blue"))
            while True:
                try:
                    markets_df = self.fetch_market_data()
                    similar_markets = self.arbitrage_detector.find_similar_markets(markets_df)
                    opportunities = self.arbitrage_detector.detect_arbitrage(similar_markets)
                    self.display_opportunities(opportunities)
                except KeyboardInterrupt:
                    console.print(Panel("Shutting down Arbitrage Bot...", style="bold red"))
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    raise e
                else:
                    logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
                    time.sleep(CHECK_INTERVAL)
                
if __name__ == "__main__":
    bot = ArbitrageBot()
    bot.run() 