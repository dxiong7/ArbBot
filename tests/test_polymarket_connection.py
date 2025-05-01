import os
from dotenv import load_dotenv
from arbbot.polymarket_client import PolymarketClient
import logging

logger = logging.getLogger(__name__)

def test_polymarket_connection():
    """Test the connection to Polymarket and basic functionality."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize the client
        private_key = os.getenv('POLYMARKET_PRIVATE_KEY', '').strip("'").strip('"').replace('0x', '')
        if not private_key:
            raise ValueError("POLYMARKET_PRIVATE_KEY not found in environment variables")
            
        client = PolymarketClient(private_key)
        logger.info("Successfully initialized PolymarketClient")
        
        # Test getting markets
        markets, next_offset = client.get_markets(limit=5)
        logger.info(f"Successfully retrieved markets")
        logger.info(f"Number of markets: {len(markets)}")
        logger.info(f"Next offset: {next_offset}")
        
        # Show details of first market if available
        if markets:
            first_market = markets[0]
            logger.info("\nFirst market details:")
            for key, value in first_market.items():
                if isinstance(value, (str, int, float, bool)):
                    logger.info(f"{key}: {value}")
                else:
                    logger.info(f"{key}: [complex value]")
            
            # Log market ID for reference
            market_id = first_market.get('id')
            logger.info(f"\nMarket ID: {market_id}")
            
            # TODO: Orderbook functionality to be implemented
            # The ClobClient API needs to be investigated for the correct orderbook method
        else:
            logger.warning("No markets found")
        
        logger.info("\nAll tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    test_polymarket_connection()