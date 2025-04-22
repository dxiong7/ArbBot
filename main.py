import logging
import time
from typing import List, Dict
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from kalshi_client import KalshiClient
from polymarket_client import PolymarketClient
from market_processor import MarketProcessor
from arbitrage_detector import ArbitrageDetector
from config import (
    KALSHI_API_KEY, KALSHI_PRIVATE_KEY, POLYMARKET_API_KEY, POLYMARKET_PRIVATE_KEY,
    CHECK_INTERVAL, SIMILARITY_THRESHOLD, MIN_PROFIT_THRESHOLD,
    LOG_LEVEL, LOG_FILE
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
console = Console()

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
            print("Got markets from Kalshi")
            print()
            polymarket_markets, _ = self.polymarket_client.get_markets(active_only=True)
            # If PolymarketClient.get_markets still returns a tuple, extract only the list
            if isinstance(polymarket_markets, tuple):
                polymarket_markets = polymarket_markets[0]
            print("Got markets from Polymarket")
            print()
            
            # Process and normalize the data
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
        
    def run(self) -> None:
        """Main application loop."""
        console.print(Panel("Starting Arbitrage Bot...", style="bold blue"))
        
        while True:
            try:
                # Fetch and process market data
                markets_df = self.fetch_market_data()
                
                # Find similar markets
                similar_markets = self.arbitrage_detector.find_similar_markets(markets_df)
                
                # Detect arbitrage opportunities
                opportunities = self.arbitrage_detector.detect_arbitrage(similar_markets)
                
                # Display results
                self.display_opportunities(opportunities)
                
                # Wait for next check
                logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                console.print(Panel("Shutting down Arbitrage Bot...", style="bold red"))
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
                
if __name__ == "__main__":
    bot = ArbitrageBot()
    bot.run() 