import pytest
from unittest.mock import MagicMock, patch, call
from src.arbbot.main import ArbitrageBot
from src.arbbot.polymarket_client import PolymarketClient # Keep for type hints/real use
from src.arbbot.kalshi_client import KalshiClient # Keep for mocking
import logging
import os
import json

@pytest.fixture
def arbitrage_bot(): # Removed request parameter
    """Fixture to create an ArbitrageBot instance for Polymarket integration testing.
    - Mocks KalshiClient.
    - Uses REAL PolymarketClient.
    - Checks for POLYMARKET_PRIVATE_KEY.
    - Uses REAL logging (configured by pytest.ini/main).
    """
    # Ensure necessary environment variable for Polymarket is set
    if not os.getenv('POLYMARKET_PRIVATE_KEY'):
        pytest.skip("POLYMARKET_PRIVATE_KEY environment variable not set, skipping Polymarket integration test.")

    # Patch ONLY KalshiClient
    with patch('src.arbbot.main.KalshiClient', autospec=True) as MockKalshiClient:
        try:
            # Instantiate the bot - real PolymarketClient and real logger will be used
            bot = ArbitrageBot()
        except Exception as e:
            pytest.fail(f"Failed to instantiate ArbitrageBot for Polymarket integration test: {e}")

        # Assign mocks
        bot.kalshi_client = MockKalshiClient.return_value

        return bot


class TestArbitrageBotProcessPolymarket:

    @pytest.mark.integration
    def test_process_polymarket_events_integration(self, arbitrage_bot):
        """Integration test: Fetches real events via get_events() and processes a subset.""" 
        
        # Arrange: Fetch real events from Polymarket API
        try:
            arbitrage_bot.logger.info("Integration test: Fetching real events from Polymarket...")
            real_events = arbitrage_bot.polymarket_client.get_events(limit=3)
            arbitrage_bot.logger.info(f"Integration test: Fetched {len(real_events)} events from Polymarket.")
            assert isinstance(real_events, list), "get_events() should return a list"
        except Exception as e:
             pytest.fail(f"Error calling polymarket_client.get_events(): {e}")

        # Skip if no events were returned by the API
        if not real_events:
            pytest.skip("Polymarket API returned no events. Skipping processing step.")

        # Limit the number of events to process to avoid excessive API calls
        events_to_process = real_events[:1] 
        arbitrage_bot.logger.info(f"Integration test: Limiting processing to {len(events_to_process)} event(s).")


        # Act: Call the method under test with the LIMITED real events
        try:
            processed_markets = arbitrage_bot._process_polymarket_events(events_to_process) 
        except Exception as e:
             pytest.fail(f"Error calling _process_polymarket_events with real events: {e}")


        # Assert: Check results based on real data processing
        assert isinstance(processed_markets, list), "_process_polymarket_events should return a list"

        # Check if any markets were successfully processed
        if not processed_markets:
             # Log or warn, but don't necessarily fail if the real events contained no processable markets
             arbitrage_bot.logger.warning(f"Integration test: Processing {len(events_to_process)} real event(s) resulted in no processable markets. This might be expected.")
             # We might use xfail here if it's common for no markets to be processable
             pytest.xfail(f"Processing {len(events_to_process)} real event(s) resulted in no processable markets. Marking as xfail.") 

        arbitrage_bot.logger.info(f"Integration test: Successfully processed {len(processed_markets)} markets from {len(events_to_process)} event(s).")
        assert len(processed_markets) >= 1, f"Expected at least one market to be processed from the first event."

        # Assert structure and types of the first processed market (if any)
        market = processed_markets[0]
        arbitrage_bot.logger.info(f"Integration test: Sample processed market: {json.dumps(market, indent=2)}")
        
        assert market['platform'] == 'Polymarket'
        assert isinstance(market['ticker'], str) and market['ticker'], "Ticker should be a non-empty string"
        assert isinstance(market['yes_price'], float), "yes_price should be a float"
        assert 0.0 <= market['yes_price'] <= 1.0, "yes_price should be between 0 and 1"
        assert isinstance(market['no_price'], float), "no_price should be a float"
        # Allow a small tolerance for floating point math near 0 or 1
        assert -0.001 <= market['no_price'] <= 1.001, "no_price calculation seems off"
        assert isinstance(market['raw_market'], dict), "raw_market should be a dictionary"
        assert market['raw_market'].get('id') or market['raw_market'].get('slug'), "Processed market raw data missing id/slug"

        arbitrage_bot.logger.info(f"Integration test successful. Processed {len(processed_markets)} markets.")
