import unittest
import logging
from polymarket_client import PolymarketClient
from dotenv import load_dotenv
import os

# run with PYTHONPATH=/Users/daniel/Developer/ArbitrageBot python3 test_market_integration.py -v
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestMarketIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before running tests."""
        load_dotenv()
        # Initialize Polymarket client with real credentials
        cls.polymarket_key = os.getenv('POLYMARKET_PRIVATE_KEY', '').strip("'").strip('"')
        cls.polymarket_client = PolymarketClient(cls.polymarket_key)
        logger.info("Initialized Polymarket client")

    def test_market_data_structure(self):
        """Test that Polymarket returns market data in expected format"""
        logger.info("Testing market data structure...")
        
        # Test Polymarket market structure
        poly_markets = self.polymarket_client.get_markets(limit=1)
        self.assertTrue(isinstance(poly_markets, list))
        if poly_markets:
            market = poly_markets[0]
            logger.info(f"Retrieved Polymarket market: {market.get('question', 'N/A')}")
            self.assertIn('question', market)
            self.assertIn('outcomes', market)

    def test_market_data(self):
        """Test market data retrieval using direct API"""
        logger.info("Testing direct market data retrieval...")
        
        # Get markets directly from API
        markets = self.polymarket_client.get_markets_direct()
        self.assertTrue(isinstance(markets, list))
        if markets:
            market = markets[0]
            logger.info(f"Testing market data for market with condition_id: {market.get('condition_id', 'N/A')}")
            # Verify market structure
            self.assertIn('condition_id', market)
            self.assertIn('tokens', market)
            self.assertIn('active', market)
            
            # Verify token structure
            tokens = market.get('tokens', [])
            if tokens:
                token = tokens[0]
                self.assertIn('token_id', token)
                self.assertIn('outcome', token)
                self.assertIn('price', token)
                logger.info(f"Market outcome: {token.get('outcome', 'N/A')} with price: {token.get('price', 'N/A')}")
            
            logger.info(f"Market data retrieved successfully for {len(markets)} markets")

    def test_market_filtering(self):
        """Test market filtering capabilities"""
        logger.info("Testing market filtering...")
        
        # Test Polymarket active markets filtering
        poly_markets = self.polymarket_client.get_markets(
            active_only=True,
            limit=5
        )
        poly_count = len(poly_markets)
        logger.info(f"Retrieved {poly_count} active Polymarket markets")
        self.assertLessEqual(poly_count, 5)

    def test_price_data_validation(self):
        """Test price data validation and formatting"""
        logger.info("Testing price data validation...")
        
        # Test Polymarket price validation
        poly_markets = self.polymarket_client.get_markets(limit=1)
        if poly_markets:
            market = poly_markets[0]
            logger.info(f"Validating Polymarket prices for: {market.get('question', 'N/A')}")
            best_bid = market.get('bestBid')
            best_ask = market.get('bestAsk')
            if best_bid is not None:
                self.assertIsInstance(float(best_bid), float)
                logger.info(f"Valid bestBid price: {best_bid}")
            if best_ask is not None:
                self.assertIsInstance(float(best_ask), float)
                logger.info(f"Valid bestAsk price: {best_ask}")

if __name__ == '__main__':
    unittest.main()
