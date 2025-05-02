import requests
from typing import Dict, List, Optional, Any
import logging
import base64
import time
import json
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from arbbot.config import KALSHI_BASE_URL

class KalshiClient:
    def __init__(self, key_id: str, private_key: rsa.RSAPrivateKey):
        self.key_id = key_id
        self.private_key = private_key
        self.session = requests.Session()
        self.last_api_call = datetime.now()
        self.host = KALSHI_BASE_URL
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def request_headers(self, method: str, path: str) -> Dict[str, Any]:
        """Generates the required authentication headers for API requests."""
        current_time_milliseconds = int(time.time() * 1000)
        timestamp_str = str(current_time_milliseconds)
        # Remove query params from path
        path_parts = path.split('?')
        msg_string = timestamp_str + method + path_parts[0]
        signature = self.sign_pss_text(msg_string)
        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }
        return headers

    def sign_pss_text(self, text: str) -> str:
        """Signs the text using RSA-PSS and returns the base64 encoded signature."""
        message = text.encode('utf-8')
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e

    def rate_limit(self) -> None:
        """Built-in rate limiter to prevent exceeding API rate limits."""
        THRESHOLD_IN_MILLISECONDS = 100
        now = datetime.now()
        threshold_in_microseconds = 1000 * THRESHOLD_IN_MILLISECONDS
        threshold_in_seconds = THRESHOLD_IN_MILLISECONDS / 1000
        if now - self.last_api_call < timedelta(microseconds=threshold_in_microseconds):
            time.sleep(threshold_in_seconds)
        self.last_api_call = datetime.now()

    def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated GET request to the Kalshi API."""
        self.rate_limit()
        response = self.session.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=params
        )
        response.raise_for_status()
        return response.json()

    def post(self, path: str, body: dict) -> Any:
        """Performs an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        response = self.session.post(
            self.host + path,
            json=body,
            headers=self.request_headers("POST", path)
        )
        response.raise_for_status()
        return response.json()

    # Gets all multi-leg mutually exclusive events
    def get_all_multileg_exclusive_events(self, batch_size: int = 200, max_expiry_months: int = 4) -> list:
        """Retrieve all available events from Kalshi using pagination.
        
        Args:
            batch_size: Number of events to fetch per request
            max_expiry_months: Only return events expiring within this many months
            
        Returns:
            List of all active events with their nested markets
        """
        all_events = []
        cursor = None
        total_fetched = 0
        total_within_expiry = 0
        print(f"Fetching events with max_expiry_months={max_expiry_months} and are mutually exclusive and multi-leg")
        # Calculate cutoff date in UTC and format it to match API format
        cutoff_date = (datetime.now(timezone.utc) + timedelta(days=30 * max_expiry_months)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        while True:
            batch = self.get_events_batch(limit=batch_size, cursor=cursor)
            if not batch or not batch.get('events'):
                break
                
            events = batch['events']
            
            # Filter events by expiration
            filtered_events = []
            for event in events:
                markets = event.get('markets', [])
                if not markets:
                    continue
                    
                # Get expiration from first market (prefer expected_expiration_time if exists)
                close_time = markets[0].get('expected_expiration_time') or markets[0].get('close_time')
                if not close_time:
                    continue
                event_mutually_exclusive = event.get('mutually_exclusive', False)
                event_filters = event_mutually_exclusive and close_time <= cutoff_date and len(markets) > 1
                if event_filters:
                    filtered_events.append(event)

            
            all_events.extend(filtered_events)
            total_fetched += len(events)
            total_within_expiry += len(filtered_events)
            
            # Log progress
            self.logger.info(f"Fetched {len(events)} events, {len(filtered_events)} within {max_expiry_months} months (Total: {total_fetched}, Within expiry: {total_within_expiry})")
            
            # Check if we have a next cursor
            cursor = batch.get('cursor')
            if not cursor:
                break
            time.sleep(0.2)
                
        return all_events

    def get_events_batch(self, limit: int = 100, cursor: Optional[str] = None) -> dict:
        """Retrieve a single batch of events from Kalshi.
        
        Args:
            limit: Number of events to fetch in this batch
            cursor: Pagination cursor from previous request
            
        Returns:
            Dict containing:
                - events: List of event objects
                - cursor: Next page cursor (if more results exist)
        """
        params = {
            "limit": limit,
            "with_nested_markets": True,
            "status": "open",  # Only get open events
            "include_market_info": True  # Include full market details
        }
        if cursor:
            params["cursor"] = cursor
            
        try:
            response = self.get("/trade-api/v2/events", params=params)
            
            # Validate response format
            if not isinstance(response, dict):
                self.logger.error(f"Unexpected response type: {type(response)}")
                return {}
                
            if 'events' not in response:
                self.logger.error(f"No 'events' key in response: {response}")
                return {}
                
            if not isinstance(response['events'], list):
                self.logger.error(f"'events' is not a list: {type(response['events'])}")
                return {}
                
            return {
                'events': response['events'],
                'cursor': response.get('cursor')
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching events batch: {e}")
            return {}

    def get_event(self, event_ticker: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single event by its ticker.
        
        Args:
            event_ticker: The ticker of the event to fetch
            
        Returns:
            Dict containing the event data if found, None otherwise
        """
        try:
            response = self.get(f"/trade-api/v2/events/{event_ticker}", params={
                "with_nested_markets": True,
                "include_market_info": True
            })
            
            if not isinstance(response, dict):
                self.logger.error(f"Unexpected response type: {type(response)}")
                return None
                
            if 'event' not in response:
                self.logger.error(f"No 'event' key in response: {response}")
                return None
                
            return response['event']
            
        except Exception as e:
            self.logger.error(f"Error fetching event {event_ticker}: {e}")
            return None
            
    def get_markets(self, limit: int = 200, cursor: Optional[str] = None) -> list:
        """Retrieve available markets from Kalshi as a list of dicts."""
        params = {
            "limit": limit,
            "status": "open"
        }
        if cursor:
            params["cursor"] = cursor
        response = self.get(self.markets_url, params=params)
        # Expecting response to be a dict with 'markets' key
        if isinstance(response, dict) and 'markets' in response and isinstance(response['markets'], list):
            return response['markets']
        elif isinstance(response, list):
            return response
        else:
            self.logger = getattr(self, 'logger', None)
            if self.logger:
                self.logger.error(f"Unexpected Kalshi markets response format: {response}")
            return []

    def get_market_details(self, market_id: str) -> Dict:
        """Get detailed information about a specific market."""
        return self.get(f"{self.markets_url}/{market_id}")

    def get_market_orderbook(self, market_id: str) -> Dict:
        """Get the orderbook for a specific market."""
        return self.get(f"{self.markets_url}/{market_id}/orderbook") 