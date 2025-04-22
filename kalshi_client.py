import requests
from typing import Dict, List, Optional, Any
import logging
import base64
import time
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from config import KALSHI_BASE_URL

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

    def get_markets(self, limit: int = 100, cursor: Optional[str] = None) -> list:
        """Retrieve available markets from Kalshi as a list of dicts."""
        params = {"limit": limit}
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

    def get_orderbook(self, market_id: str) -> Dict:
        """Get the orderbook for a specific market."""
        return self.get(f"{self.markets_url}/{market_id}/orderbook") 