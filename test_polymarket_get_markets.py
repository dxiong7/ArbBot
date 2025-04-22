import os
from dotenv import load_dotenv
from polymarket_client import PolymarketClient
import logging

def test_polymarket_get_active_markets():
    """Test the Polymarket API for fetching only active markets and log the results."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize the client
        private_key = os.getenv('POLYMARKET_PRIVATE_KEY', '')
        if not private_key:
            raise ValueError("POLYMARKET_PRIVATE_KEY not found in environment variables")
        client = PolymarketClient(private_key)
        logger.info("Successfully initialized PolymarketClient")

        # Fetch and print the first 5 active markets in a clean format
        markets, next_offset = client.get_markets(active_only=True, limit=5)
        print(f"First 5 active markets (count: {len(markets)}):\n")
        for i, market in enumerate(markets, 1):
            title = market.get('groupItemTitle') or market.get('title') or market.get('slug') or 'N/A'
            question = market.get('question', 'N/A')
            outcomes = market.get('outcomes', 'N/A')
            if isinstance(outcomes, str):
                try:
                    import json
                    outcomes = json.loads(outcomes)
                except Exception:
                    pass
            best_bid = market.get('bestBid', 'N/A')
            best_ask = market.get('bestAsk', 'N/A')
            end_date = market.get('endDate', 'N/A')
            yes_price = best_bid if outcomes and outcomes[0] == 'Yes' else 'N/A'
            no_price = best_ask if outcomes and outcomes[-1] == 'No' else 'N/A'
            print(f"Market {i}:")
            print(f"  Title    : {title}")
            print(f"  Question : {question}")
            print(f"  Outcomes : {outcomes}")
            print(f"  Best Bid : {best_bid}")
            print(f"  Best Ask : {best_ask}")
            print(f"  End Date : {end_date}")
            print(f"  Yes Price: {yes_price}")
            print(f"  No Price : {no_price}")
            description = market.get('description', 'N/A')
            print(f"  Description: {description}")
            # Print events (if any)
            events = market.get('events', [])
            if isinstance(events, str):
                try:
                    import json
                    events = json.loads(events)
                except Exception:
                    events = []
            if events:
                print(f"  Events:")
                for event in events:
                    event_title = event.get('title', 'N/A')
                    event_desc = event.get('description', 'N/A')
                    print(f"    - Title      : {event_title}")
                    print(f"      Description: {event_desc}")
            print('-' * 60)
        if next_offset:
            print(f"More markets available. Next offset: {next_offset}")
        else:
            print("No more markets available.")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_polymarket_get_active_markets()
