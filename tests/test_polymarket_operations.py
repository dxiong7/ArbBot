import os
import pytest
from dotenv import load_dotenv
from arbbot.polymarket_client import PolymarketClient
import logging

logger = logging.getLogger(__name__)

@pytest.fixture
def client():
    """Create a PolymarketClient instance for testing."""
    load_dotenv()
    private_key = os.getenv('POLYMARKET_PRIVATE_KEY', '').strip("'").strip('"').replace('0x', '')
    if not private_key:
        pytest.skip("POLYMARKET_PRIVATE_KEY not found in environment variables")
    return PolymarketClient(private_key)

def test_get_markets_direct(client):
    """Test fetching markets using the simplified-markets endpoint."""
    markets = client.get_markets_direct()
    assert isinstance(markets, list), "Markets should be a list"
    if markets:
        first_market = markets[0]
        assert isinstance(first_market, dict), "Market should be a dictionary"
        # Log first market structure for debugging
        logger.info(f"First market keys: {first_market.keys()}")
        logger.info(f"First market ID: {first_market.get('id')}")

def test_iter_markets(client):
    """Test the market iterator."""
    count = 0
    market_ids = set()
    
    # Test with a small limit to ensure pagination works
    for market in client.iter_markets(limit=2):
        assert isinstance(market, dict), "Each market should be a dictionary"
        market_id = market.get('id')
        assert market_id is not None, "Market should have an ID"
        assert market_id not in market_ids, "Market IDs should be unique"
        market_ids.add(market_id)
        count += 1
        if count >= 5:  # Limit the number of markets for testing
            break
    
    assert count > 0, "Should have retrieved at least one market"
    logger.info(f"Retrieved {count} markets through iterator")

def test_get_market_data(client):
    """Test fetching detailed market data."""
    # First get a market ID from the markets list
    markets, _ = client.get_markets(limit=1)
    assert markets, "Should have at least one market to test with"
    
    market_id = markets[0]['id']
    market_data = client.get_market_data(market_id)
    
    assert isinstance(market_data, dict), "Market data should be a dictionary"
    assert market_data.get('id') == market_id, "Market data should be for the requested market"
    logger.info(f"Retrieved market data for market ID: {market_id}")

def test_get_orderbook(client):
    """Test fetching the orderbook for a market."""
    # First get a market ID from the markets list
    markets, _ = client.get_markets(limit=1)
    assert markets, "Should have at least one market to test with"
    
    market_id = markets[0]['id']
    orderbook = client.get_orderbook(market_id)
    
    assert isinstance(orderbook, dict), "Orderbook should be a dictionary"
    assert 'yes' in orderbook, "Orderbook should have a 'yes' section"
    assert 'no' in orderbook, "Orderbook should have a 'no' section"
    
    # Check structure of YES orderbook
    yes_book = orderbook['yes']
    assert isinstance(yes_book, dict), "YES orderbook should be a dictionary"
    
    # Check structure of NO orderbook
    no_book = orderbook['no']
    assert isinstance(no_book, dict), "NO orderbook should be a dictionary"
    
    # Log orderbook details for debugging
    logger.info(f"Orderbook for market ID: {market_id}")
    logger.info(f"YES token orderbook keys: {yes_book.keys()}")
    logger.info(f"NO token orderbook keys: {no_book.keys()}")

@pytest.mark.skip(reason="Order creation requires real funds and should be tested in a separate environment")
def test_create_and_cancel_order(client):
    """Test creating and canceling an order."""
    # First get a market ID from the markets list
    markets, _ = client.get_markets(limit=1)
    assert markets, "Should have at least one market to test with"
    
    market_id = markets[0]['id']
    
    # Create a small test order
    order = client.create_order(
        market_id=market_id,
        side="buy",  # or "sell"
        price=0.5,   # Example price
        size=1.0     # Minimum order size
    )
    
    assert isinstance(order, dict), "Order response should be a dictionary"
    assert 'id' in order, "Order should have an ID"
    
    order_id = order['id']
    logger.info(f"Created test order with ID: {order_id}")
    
    # Cancel the test order
    cancel_result = client.cancel_order(order_id)
    assert cancel_result.get('success', False), "Order cancellation should be successful"
    logger.info(f"Successfully cancelled order {order_id}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
