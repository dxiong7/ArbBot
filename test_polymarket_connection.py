import os
from dotenv import load_dotenv
from polymarket_client import PolymarketClient
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        markets = client.get_markets()
        logger.info(f"Successfully retrieved markets")
        logger.info(f"Markets response type: {type(markets)}")
        logger.info(f"Markets content: {markets}")
        
        # Only proceed with market details if we have valid market data
        if isinstance(markets, dict) and markets.get('markets'):
            first_market = markets['markets'][0]
            logger.info("First market details:")
            logger.info(f"Market ID: {first_market.get('id')}")
            logger.info(f"Question: {first_market.get('question')}")
            logger.info(f"Current Price: {first_market.get('current_price')}")
            
            # Test getting orderbook for the first market
            market_id = first_market['id']
            orderbook = client.get_orderbook(market_id)
            logger.info(f"Successfully retrieved orderbook for market {market_id}")
            logger.info(f"Bids: {len(orderbook.get('bids', []))}")
            logger.info(f"Asks: {len(orderbook.get('asks', []))}")
        else:
            logger.warning("No markets found or unexpected response format")
            logger.info(f"Raw markets response: {markets}")
        
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_polymarket_connection() 