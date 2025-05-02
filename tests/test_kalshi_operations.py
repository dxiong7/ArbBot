import pytest
import json
from arbbot.kalshi_client import KalshiClient
from arbbot.config import get_config, load_kalshi_private_key
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

@pytest.fixture
def client():
    """Create a KalshiClient instance for testing."""
    key_id = get_config('KALSHI_API_KEY')
    if not key_id:
        pytest.skip("KALSHI_API_KEY not found in environment variables")
        
    private_key = load_kalshi_private_key()
    if not private_key:
        pytest.skip("Failed to load Kalshi private key from kalshi_private_key.pem")
        
    return KalshiClient(key_id=key_id, private_key=private_key)

def test_get_events_batch(client):
    """Test fetching a batch of events."""
    events = client.get_events_batch(limit=5)
    assert isinstance(events, dict), "Events response should be a dictionary"
    assert 'events' in events, "Response should contain 'events' key"
    assert isinstance(events['events'], list), "Events should be a list"
    
    if events['events']:
        first_event = events['events'][0]
        assert isinstance(first_event, dict), "Event should be a dictionary"
        # Log first event structure for debugging
        logger.info(f"First event keys: {first_event.keys()}")
        logger.info(f"First event title: {first_event.get('title')}")
        
        # Check for required fields
        assert 'markets' in first_event, "Event should have markets"
        assert isinstance(first_event['markets'], list), "Markets should be a list"

def test_get_all_multileg_exclusive_events(client):
    """Test fetching all multi-leg mutually exclusive events."""
    events = client.get_all_multileg_exclusive_events(batch_size=100, max_expiry_months=1)
    assert isinstance(events, list), "Events should be a list"
    
    if events:
        first_event = events[0]
        assert isinstance(first_event, dict), "Event should be a dictionary"
        assert 'markets' in first_event, "Event should have markets"
        assert len(first_event['markets']) > 1, "Multi-leg event should have multiple markets"
        assert first_event.get('mutually_exclusive', False), "Event should be mutually exclusive"
        
        # Check expiration time is within range
        expiration_time = first_event['markets'][0].get('expiration_time')
        if expiration_time:
            expiry_date = datetime.fromisoformat(expiration_time.replace('Z', '+00:00'))
            one_month_from_now = datetime.now(timezone.utc) + timedelta(days=30)
            assert expiry_date <= one_month_from_now, "Event should expire within one month"

def test_get_event(client):
    """Test fetching a single event with given market ticker"""
    # First get an event ticker from the events list
    events = client.get_events_batch(limit=1)
    if not events['events']:
        pytest.skip("No events available for testing")
        
    # Get first event
    first_event = events['events'][0]
    event_ticker = first_event.get('event_ticker')
    if not event_ticker:
        pytest.skip("Event has no event_ticker")
    event_ticker = 'KXAUSTRALIA'.upper()
    logger.info(f"Fetching event with ticker: {event_ticker}")
    event = client.get_event(event_ticker)

    logger.info(json.dumps(event, indent=4))
    assert isinstance(event, dict), "Event should be a dictionary"
    assert 'markets' in event, "Event should have markets"
    assert isinstance(event['markets'], list), "Markets should be a list"
    assert event.get('event_ticker') == event_ticker, "Event ticker should match"
    
def test_get_market_orderbook(client):
    """Test fetching orderbook for a market."""
    # First get a market ID from an event
    events = client.get_events_batch(limit=1)
    if not events['events']:
        pytest.skip("No events available for testing")
    
    market_id = events['events'][0]['markets'][0]['id']
    orderbook = client.get_market_orderbook(market_id)
    
    assert isinstance(orderbook, dict), "Orderbook should be a dictionary"
    assert 'yes' in orderbook, "Orderbook should have 'yes' side"
    assert 'no' in orderbook, "Orderbook should have 'no' side"
    
    # Check orderbook structure
    for side in ['yes', 'no']:
        assert isinstance(orderbook[side], list), f"{side} orders should be a list"
        if orderbook[side]:
            first_order = orderbook[side][0]
            assert len(first_order) == 2, "Order should have price and quantity"
            assert isinstance(first_order[0], int), "Price should be an integer (in cents)"
            assert isinstance(first_order[1], int), "Quantity should be an integer"

def test_pagination(client):
    """Test event pagination."""
    batch_size = 2
    total_events = []
    cursor = None
    
    # Get first batch
    first_batch = client.get_events_batch(limit=batch_size, cursor=cursor)
    assert len(first_batch['events']) <= batch_size, "Batch size limit should be respected"
    total_events.extend(first_batch['events'])
    
    # Get second batch using cursor
    cursor = first_batch.get('cursor')
    if cursor:
        second_batch = client.get_events_batch(limit=batch_size, cursor=cursor)
        assert len(second_batch['events']) <= batch_size, "Second batch size limit should be respected"
        
        # Events should be different between batches
        first_ids = {event['id'] for event in first_batch['events']}
        second_ids = {event['id'] for event in second_batch['events']}
        assert not first_ids.intersection(second_ids), "Events should not be duplicated between batches"

def test_rate_limiting(client):
    """Test rate limiting behavior."""
    # Make multiple quick requests
    for _ in range(3):
        response = client.get_events_batch(limit=1)
        assert response is not None, "Rate limited requests should still succeed"
        assert 'events' in response, "Rate limited requests should return valid data"
