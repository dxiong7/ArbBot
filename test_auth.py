import logging
from kalshi_client import KalshiClient
from config import KALSHI_API_KEY, KALSHI_PRIVATE_KEY, KALSHI_BASE_URL

# Configure logging
logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_kalshi_auth():
    try:
        # Initialize client with the RSA key object
        client = KalshiClient(KALSHI_API_KEY, KALSHI_PRIVATE_KEY)
        
        # Test API connection by fetching markets
        logger.info("Testing Kalshi API connection...")
        markets = client.get_markets(limit=5)
        
        logger.info("Successfully connected to Kalshi API!")
        logger.info(f"Retrieved {len(markets.get('markets', []))} markets")
        
        # Print first market details if available
        if markets.get('markets'):
            first_market = markets['markets'][0]
            logger.info(f"First market: {first_market.get('ticker')} - {first_market.get('title')}")
            
    except Exception as e:
        logger.error(f"Authentication test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_kalshi_auth() 