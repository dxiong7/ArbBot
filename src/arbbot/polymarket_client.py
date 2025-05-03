import os
import requests
from typing import Dict, List, Optional, Tuple
import logging
from datetime import timedelta
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from py_clob_client.constants import POLYGON
from py_clob_client.clob_types import OrderArgs
from py_clob_client.order_builder.constants import BUY, SELL
from datetime import datetime, timezone

class PolymarketClient:
    def __init__(self, private_key: str):
        self.host = "https://gamma-api.polymarket.com"
        self.clob_endpoint = "https://clob.polymarket.com"
        self.gamma_endpoint = "https://gamma-api.polymarket.com"
        # Ensure private key is properly formatted as hex
        if not private_key.startswith('0x'):
            private_key = f'0x{private_key}'
        self.private_key = private_key
        self.chain_id = POLYGON
        self.logger = logging.getLogger(__name__)
        creds = ApiCreds(
        api_key='0x4a8242694a8c194d51cda4b53e5a47d5315d0acdbf4a3adb36b0289824abc02e',
        api_secret='yUzWKGhKQ5FV-WlM7SQjv7l1gj9TPZcza1SQ8lzG3ds=',
        api_passphrase='0f022b13ba7595386d9a6234b6f37ba4f3e6e36a8b78abca648c36d90ed2177a',
        )
        try:
            self.logger.info("Initializing ClobClient with host: %s, key: %s, chain_id: %s, creds: %s", self.host, private_key, self.chain_id, creds)
            self.client = ClobClient(self.host, key=private_key, chain_id=self.chain_id, creds=creds)
            self.logger.info("ClobClient initialized successfully")
            #self._setup_api_credentials()
        except Exception as e:
            self.logger.error(f"Failed to initialize ClobClient: {e}")
            raise
            
    def _setup_api_credentials(self) -> None:
        """Set up API credentials for the client."""
        try:
            self.logger.info("Setting up API credentials...")
            api_creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(api_creds)
            self.logger.info("API credentials set up successfully")
        except Exception as e:
            self.logger.error(f"Failed to set up API credentials: {e}")
            raise
            

    def get_markets(self, active_only=True, limit=100, offset=0):
        """
        Retrieve a single page of markets from the Polymarket Gamma Markets API.
        :param active_only: If True, only fetch active markets.
        :param limit: Number of markets per page (max 100).
        :param offset: The offset for pagination.
        :return: List of market dicts.
        """
        try:
            self.logger.info(f"Fetching markets from Gamma Markets API (page offset {offset})...")
            base_url = self.gamma_endpoint + "/markets"
            active_only_val = "false"
            if active_only:
                active_only_val = "true"
            params = {
                "limit": limit,
                "offset": offset,
                "closed": "false",
                "archived": "false",
                "active": active_only_val
            }
            resp = requests.get(base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
            markets = data
            if not isinstance(markets, list):
                self.logger.error(f"Unexpected response format: {data}")
                raise ValueError(f"Unexpected response format: {data}")
            self.logger.info(f"Fetched {len(markets)} markets (offset {offset})")
            next_offset = offset + len(markets) if len(markets) == limit else None
            return markets, next_offset
        except Exception as e:
            self.logger.error(f"Failed to fetch markets from Gamma Markets API: {e}")
            raise

    def get_events(self, active_only=True, limit=100):
        """Get all events from the Polymarket Gamma Markets API."""
        try:
            self.logger.info("Fetching events from Gamma Markets API...")
            max_expiry_date = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            min_expiry_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
            self.logger.info(f"Fetching events with min_expiry_date: {min_expiry_date}, max_expiry_date: {max_expiry_date}")
            query_params = {
                "limit": limit,
                "offset": 0,
                "closed": "false",
                "archived": "false",
                "active": "true",
                "end_date_min": min_expiry_date,
                "end_date_max": max_expiry_date
            }
            resp = requests.get(self.gamma_endpoint + "/events", params=query_params)
            resp.raise_for_status()
            events = resp.json()
            self.logger.info(f"Fetched {len(events)} events")
            return events
        except Exception as e:
            self.logger.error(f"Failed to fetch events from Gamma Markets API: {e}")
            raise

    def iter_markets(self, active_only=True, limit=100):
        """
        Generator that yields all markets from the Polymarket Gamma Markets API, handling pagination internally.
        :param active_only: If True, only fetch active markets.
        :param limit: Number of markets per page (max 100).
        :yield: Individual market dicts.
        """
        offset = 0
        while True:
            markets, next_offset = self.get_markets(active_only=active_only, limit=limit, offset=offset)
            if not markets:
                break
            for market in markets:
                yield market
            if next_offset is None:
                break
            offset = next_offset

            
    def get_market_data(self, market_id: str) -> Dict:
        """Get detailed information about a specific market."""
        try:
            return self.client.get_market(market_id)
        except Exception as e:
            self.logger.error(f"Failed to fetch market data: {e}")
            raise
    
    def get_single_event(self, event_id: str) -> Dict:
        """Get detailed information about a specific event."""
        try:
            return self.client.get_event(event_id)
        except Exception as e:
            self.logger.error(f"Failed to fetch event data: {e}")
            raise
            
    def get_token_ids(self, market_id: int) -> Tuple[Optional[str], Optional[str]]:
        """Retrieve YES and NO token IDs for a given market ID."""
        try:
            # First try to get market data from CLOB client
            # TODO: Update if get_market structure changes
            market_data_clob = self.client.get_market(market_id)
            # self.logger.debug(f'CLOB get_market response for {market_id}: {market_data_clob}') # Optional detailed logging
            if market_data_clob and 'tokens' in market_data_clob:
                tokens = market_data_clob['tokens']
                if isinstance(tokens, list) and len(tokens) >= 2:
                    # Assuming order is consistent (e.g., Yes then No)
                    # Might need more robust logic if order isn't guaranteed
                    self.logger.info(f"Found token IDs via CLOB client for market {market_id}")
                    return tokens[0].get('token_id'), tokens[1].get('token_id')
                else:
                    self.logger.warning(f"CLOB client returned 'tokens' but not in expected list format for market {market_id}: {tokens}")
            else:
                 self.logger.info(f"Token IDs not found via CLOB client for market {market_id}. Falling back to Gamma API.")

        except Exception as e:
            self.logger.warning(f"Error fetching from CLOB get_market for {market_id}, falling back to Gamma API: {e}")

        # Fallback: Try getting from Gamma Markets API
        try:
            market_data_gamma = self.get_market_data(market_id)
            # self.logger.debug(f"Gamma get_market_data response for {market_id}: {market_data_gamma}") # Optional detailed logging
            
            if market_data_gamma and 'clob_token_ids' in market_data_gamma:
                token_ids = market_data_gamma['clob_token_ids']
                if isinstance(token_ids, list) and len(token_ids) >= 2:
                    self.logger.info(f"Found token IDs via Gamma API for market {market_id}")
                    return token_ids[0], token_ids[1]
                else:
                    self.logger.warning(f"Gamma API returned 'clob_token_ids' but not in expected list format for market {market_id}: {token_ids}")
            else:
                # Log why token IDs might be missing
                enable_order_book = market_data_gamma.get('enableOrderBook', 'N/A') if market_data_gamma else 'N/A'
                self.logger.warning(f"'clob_token_ids' key not found in Gamma API response for market {market_id}. enableOrderBook={enable_order_book}")
                # If order book is explicitly disabled, don't raise error, return None
                if enable_order_book is False:
                     self.logger.info(f"Order book disabled for market {market_id}, returning None for token IDs.")
                     return None, None

        except Exception as e:
             self.logger.error(f"Error fetching from Gamma get_market_data for {market_id}: {e}")

        # If neither method worked and order book wasn't explicitly disabled
        error_msg = f"Could not find token IDs for market {market_id} via CLOB or Gamma API."
        self.logger.error(error_msg)
        raise ValueError(error_msg)
            
    def get_orderbook(self, market_id: str) -> Dict:
        """Get the order book for a specific market."""
        try:
            yes_token_id, no_token_id = self.get_token_ids(market_id)
            if not yes_token_id or not no_token_id:
                raise ValueError(f"Could not find token IDs for market {market_id}")
                
            # Get orderbooks for both YES and NO tokens
            orderbooks = self.client.get_order_books([
                {'token_id': yes_token_id},
                {'token_id': no_token_id}
            ])
            
            return {
                'yes': orderbooks.get(yes_token_id, {}),
                'no': orderbooks.get(no_token_id, {})
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch orderbook: {e}")
            raise
            
    def create_order(self, market_id: str, side: str, price: float, size: float) -> Dict:
        """Create and post an order."""
        try:
            order_args = OrderArgs(
                price=price,
                size=size,
                side=BUY if side.lower() == 'buy' else SELL,
                token_id=market_id
            )
            return self.client.create_and_post_order(order_args)
        except Exception as e:
            self.logger.error(f"Failed to create order: {e}")
            raise
            
    def get_orders(self, market_id: Optional[str] = None) -> List[Dict]:
        """Get active orders, optionally filtered by market."""
        try:
            return self.client.get_orders(market_id=market_id)
        except Exception as e:
            self.logger.error(f"Failed to fetch orders: {e}")
            raise
            
    def cancel_order(self, order_id: str) -> Dict:
        """Cancel a specific order."""
        try:
            return self.client.cancel_order(order_id)
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            raise

    # Get markets directly through the CLOB client
    def get_markets_direct(self) -> Dict:
        """Alternative method to fetch markets using the CLOB client's markets endpoint."""
        try:
            self.logger.info("Fetching markets from CLOB client...")
            
            # Use the CLOB client's get_markets method
            # Pass empty string as next_cursor to get the first page
            response = self.client.get_markets("")
            
            if isinstance(response, dict) and 'markets' in response:
                markets = response['markets']
                self.logger.info(f"Successfully fetched {len(markets)} markets from CLOB client")
                if markets:
                    self.logger.info(f"First market structure: {list(markets[0].keys())}")
                return markets
            else:
                self.logger.error(f"Unexpected response format: {response}")
                raise ValueError("Unexpected response format in get_markets_direct")
                
        except Exception as e:
            self.logger.error(f"Failed to fetch markets: {e}")
            raise