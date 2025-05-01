import logging
import time
import traceback
import json
from typing import List, Dict
from datetime import datetime, timedelta
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
    LOG_LEVEL, LOG_FILE, INTERNAL_ONLY_MODE
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

    # TODO: identify binary markets correctly with only 1 outcome of yes/no the market_type field in markets is not what we;re thinking about
    def run_internal_only_mode(self):
        """Internal-only mode: Only search for arbitrage on Kalshi, starting from events."""
        console.print(Panel("Starting Kalshi Internal-Only Arbitrage Mode (events-based)...", style="bold blue"))
        while True:
            try:
                kalshi_events = self.kalshi_client.get_all_multileg_exclusive_events()
                logger.info(f"Fetched total of {len(kalshi_events)} suitable Kalshi events.")

                found_arbitrage = False
                #print(json.dumps(kalshi_events[0], indent=4, sort_keys=True))
                all_markets_have_bids = True
                for event in kalshi_events:
                    print()
                    event_title = event.get('title') or event.get('name') or event.get('ticker')
                    expiry = event.get('expiration') or event.get('end_date') or event.get('expiry')
                    markets = event.get('markets', [])
                    
                    # Skip if no markets
                    if not markets:
                        logger.info(f"Skipping event {event_title}: No markets found")
                        continue
                    # Skip if volume for all markets is 0
                    if all(market.get('volume', 0) == 0 for market in markets):
                        logger.info(f"Skipping event {event_title}: No volume found")
                        continue
                        
                    # logger.info(f"\nProcessing event: {event_title} ({len(markets)} markets)")
                    # logger.debug(f"Event data: {json.dumps(event, indent=2)}")

                    print(f"Processing event: {event_title}")
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
                        market_id = market.get('ticker')
                        if not market_id:
                            continue

                        # Track total volume
                        total_volume += market.get('volume', 0) or 0

                        try:
                            orderbook = self.kalshi_client.get_market_orderbook(market_id)
                            if not orderbook:
                                logger.error(f"Failed to get orderbook for market {market_id}")
                                continue

                            #logger.info(f"Orderbook for {market_id}: {json.dumps(orderbook, indent=2)}")
                            orderbook_data = orderbook.get('orderbook', {})
                            yes_orders = orderbook_data.get('yes', [])
                            no_orders = orderbook_data.get('no', [])
                            highest_yes_bid = None
                            highest_no_bid = None

                            # Check if market has any bids
                            has_bids = False

                            if yes_orders and len(yes_orders) > 0:
                                # Get highest bid (last element)
                                best_yes_order = yes_orders[-1]
                                highest_yes_bid = float(best_yes_order[0]) / 100.0  # Convert cents to dollars
                                min_sizes[f"{market_id}-YES"] = best_yes_order[1]
                                has_bids = True
                                
                            if no_orders and len(no_orders) > 0:
                                # Get highest bid (last element)
                                best_no_order = no_orders[-1]
                                highest_no_bid = float(best_no_order[0]) / 100.0  # Convert cents to dollars
                                min_sizes[f"{market_id}-NO"] = best_no_order[1]
                                has_bids = True

                            if has_bids:
                                markets_with_bids += 1
                            #     logger.info(f"  Market {market_id} has valid bids, total markets with bids: {markets_with_bids}")
                            # else:
                            #     logger.info(f"  Market {market_id} has no valid bids")
                            
                            # Calculate ask prices:
                            # YES ask = 1 - NO bid (if NO bid exists)
                            # NO ask = 1 - YES bid (if YES bid exists)
                            if highest_no_bid is not None:
                                yes_best_ask_price = 1.0 - highest_no_bid
                                yes_prices[market_id] = yes_best_ask_price
                                yes_sum += yes_best_ask_price
                                all_outcomes.append(f"{market_id}-YES")
                                #logger.debug(f"  {market_id}-YES: Ask={yes_best_ask_price:.4f} (from NO bid={highest_no_bid:.4f})")
                            
                            if highest_yes_bid is not None:
                                no_best_ask_price = 1.0 - highest_yes_bid
                                no_prices[market_id] = no_best_ask_price
                                no_sum += no_best_ask_price
                                all_outcomes.append(f"{market_id}-NO")
                                #logger.debug(f"  {market_id}-NO: Ask={no_best_ask_price:.4f} (from YES bid={highest_yes_bid:.4f})")
                            
                            #logger.debug(f"  Market {market_id} has bids: YES={highest_yes_bid}, NO={highest_no_bid}")
                        except Exception as e:
                            logger.error(f"Failed to get orderbook/details for market {market_id}: {e}")

                    # Only process event if we have at least 2 markets with bids
                    if markets_with_bids < 2:
                        logger.info(f"Skipping event {event_title}: Only {markets_with_bids} markets have bids")
                        continue
                        
                    logger.info(f"Processing event {event_title} with {len(all_outcomes)} outcomes ({markets_with_bids} markets with bids)")
                    # Check which side (YES or NO) offers arbitrage
                    logger.info(f"  YES Prices: {yes_prices} (Sum of all YES: {yes_sum:.4f})")
                    logger.info(f"  NO Prices: {no_prices} (Sum of all NO: {no_sum:.4f})")
                    
                    # For events with exactly one YES/NO outcome pair
                    is_single_outcome = len(markets) == 1
                    if is_single_outcome:
                        if highest_yes_bid is None or highest_no_bid is None:
                            logger.info(f"  Missing YES or NO orders for single outcome event market {market_id}")
                            continue
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
                            found_arbitrage = True
                            arbitrage_size = 1.0 - total_cost
                            if arbitrage_size <= ARBITRAGE_THRESHOLD:
                                logger.info(f"Arbitrage size {arbitrage_size:.4f} is below threshold {ARBITRAGE_THRESHOLD:.4f} for event {event_title}, Skipping.. ")
                                continue
                            console.print(Panel(f"[ARBITRAGE FOUND] Binary Event: {event_title} (Event Ticker: {event.get('ticker')})\nStrategy: Buy BOTH YES and NO", style="bold green"))
                            logger.info(f"  Strategy: Buy both YES ({yes_ask:.4f}) and NO ({no_ask:.4f})")
                            logger.info(f"  Arbitrage Size: {arbitrage_size:.4f}")
                            logger.info(f"  Total Volume: {total_volume}")
                            logger.info(f"  Expiry: {expiry}")
                            logger.info(f"  Min Sizes: {min_sizes}")
                        else:
                            logger.info(f"No arb found for single outcome event {event_title}")
                            
                    else:
                        #logger.info(f"  Event: {event_title} detected to be multi-outcome with {len(all_outcomes)} outcomes")
                        # For multi-outcome events:
                        # An arbitrage exists if either:
                        # 1. Sum of all YES prices < 1.0 (can buy all YES outcomes for less than $1)
                        # 2. Sum of all NO prices < 1.0 (can buy all NO outcomes for less than $1)
                        if yes_prices and yes_sum < 1.0:
                            logger.info('Checking for possible arb')
                            #logger.info(json.dumps(event, indent=4))
                            found_arbitrage = True
                            arbitrage_size = 1.0 - yes_sum
                            if arbitrage_size <= ARBITRAGE_THRESHOLD:
                                logger.info(f" {event_title} has Arbitrage size {arbitrage_size:.4f} below threshold of {ARBITRAGE_THRESHOLD:.4f}, Skipping.. ")
                                continue
                            console.print(Panel(f"[ARBITRAGE FOUND] Event: {event_title} (Event Ticker: {event.get('event_ticker')})\nStrategy: Buy ALL YES outcomes", style="bold green"))
                            logger.info(f"  Strategy: Buy ALL YES outcomes")
                            logger.info(f"  YES Prices: {yes_prices}")
                            logger.info(f"  Arbitrage Size: {arbitrage_size:.4f}")
                            logger.info(f"  Total Volume: {total_volume}")
                            logger.info(f"  Expiry: {expiry}")
                            logger.info(f"  Min Sizes: {min_sizes}")
                        elif no_prices and no_sum < 1.0:
                            logger.info('Checking for possible arb')
                            #logger.info(json.dumps(event, indent=4))
                            found_arbitrage = True
                            arbitrage_size = 1.0 - no_sum
                            if arbitrage_size <= ARBITRAGE_THRESHOLD:
                                logger.info(f"Arbitrage size {arbitrage_size:.4f} is below threshold {ARBITRAGE_THRESHOLD:.4f} for event {event_title}, Skipping.. ")
                                continue
                            console.print(Panel(f"[ARBITRAGE FOUND] Event: {event_title} (Event Ticker: {event.get('event_ticker')})\nStrategy: Buy ALL NO outcomes", style="bold green"))
                            logger.info(f"  Strategy: Buy ALL NO outcomes")
                            logger.info(f"  NO Prices: {no_prices}")
                            logger.info(f"  Arbitrage Size: {arbitrage_size:.4f}")
                            logger.info(f"  Total Volume: {total_volume}")
                            logger.info(f"  Expiry: {expiry}")
                            logger.info(f"  Min Sizes: {min_sizes}")
                        else:
                            logger.info(f"No arb found for event {event_title}")
                            continue

                
            except KeyboardInterrupt:
                console.print(Panel("Shutting down Kalshi Internal-Only Mode...", style="bold red"))
                break
            except Exception as e:
                logger.error(f"Error in internal-only mode: {e}")
                traceback.print_exc()
                raise e
                time.sleep(60)
            else:
                return

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