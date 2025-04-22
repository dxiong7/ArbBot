from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
import logging

class MarketProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_kalshi_market(self, market_data: Dict) -> Dict:
        """Convert Kalshi market data to standardized format."""
        try:
            # Ensure market_data is a dictionary
            if not isinstance(market_data, dict):
                raise ValueError("Market data must be a dictionary")
                
            standardized = {
                'market_id': market_data.get('id', ''),
                'platform': 'kalshi',
                'title': market_data.get('title', ''),
                'description': market_data.get('description', ''),
                'resolution_date': market_data.get('close_date', ''),
                'yes_price': self._get_best_price(market_data, 'yes'),
                'no_price': self._get_best_price(market_data, 'no'),
                'volume': market_data.get('volume', 0),
                'status': market_data.get('status', ''),
                'created_at': datetime.now().isoformat()
            }
            return standardized
        except Exception as e:
            self.logger.error(f"Error processing Kalshi market data: {e}")
            raise
            
    def process_polymarket_market(self, market_data: Dict) -> Dict:
        """Convert Polymarket market data to standardized format."""
        try:
            #print("Processing individual Polymarket market data...")
            # Ensure market_data is a dictionary
            if not isinstance(market_data, dict):
                raise ValueError("Market data must be a dictionary")
                
            # Extract prices from the tokens array
            yes_price = 0.0
            no_price = 0.0
            
            if 'tokens' in market_data and isinstance(market_data['tokens'], list):
                for token in market_data['tokens']:
                    if token.get('outcome', '').lower() == 'yes':
                        yes_price = float(token.get('price', 0))
                    elif token.get('outcome', '').lower() == 'no':
                        no_price = float(token.get('price', 0))
            
            # If prices are 0, try to get them from the orderbook if available
            if yes_price == 0.0 and no_price == 0.0 and 'orderbook' in market_data:
                orderbook = market_data['orderbook']
                if 'bids' in orderbook and len(orderbook['bids']) > 0:
                    yes_price = float(orderbook['bids'][0].get('price', 0))
                if 'asks' in orderbook and len(orderbook['asks']) > 0:
                    no_price = float(orderbook['asks'][0].get('price', 0))
            
            standardized = {
                'market_id': market_data.get('id', ''),
                'platform': 'polymarket',
                'title': market_data.get('question', ''),  # Polymarket uses 'question' for title
                'description': market_data.get('description', ''),
                'resolution_date': market_data.get('end_date_iso', ''),  # Using end_date_iso for proper format
                'yes_price': yes_price,
                'no_price': no_price,
                'volume': market_data.get('volume', 0),
                'status': 'active' if market_data.get('active', False) else 'inactive',
                'created_at': datetime.now().isoformat()
            }
            
            return standardized
        except Exception as e:
            self.logger.error(f"Error processing Polymarket market data: {e}")
            raise
            
    def _get_best_price(self, market_data: Dict, side: str) -> float:
        """Extract the best available price for a given side."""
        try:
            if not isinstance(market_data, dict):
                return 0.0
                
            if side == 'yes':
                return float(market_data.get('yes_price', 0))
            else:
                return float(market_data.get('no_price', 0))
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error extracting price: {e}")
            return 0.0
            
    def normalize_markets(self, kalshi_markets: List[Dict], polymarket_markets: List[Dict]) -> pd.DataFrame:
        """
        Convert all markets from Kalshi and Polymarket to a standardized DataFrame format.
        Expects both inputs to be a list of dictionaries (one per market).
        """
        try:
            processed_markets = self.normalize_kalshi_markets(kalshi_markets)
            processed_markets += self.normalize_polymarket_markets(polymarket_markets)
            self.logger.info(f"\nConverting {len(processed_markets)} total markets to DataFrame")
            df = pd.DataFrame(processed_markets)
            numeric_columns = ['yes_price', 'no_price', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            self.logger.info(f"Successfully processed {len(processed_markets)} markets")
            return df
        except Exception as e:
            self.logger.error(f"Error normalizing markets: {e}")
            raise

    def normalize_kalshi_markets(self, kalshi_markets: List[Dict]) -> list:
        """Process and standardize a list of Kalshi markets (expects a list of dicts)."""
        return [self.process_kalshi_market(m) for m in kalshi_markets if isinstance(m, dict)]

    def normalize_polymarket_markets(self, polymarket_markets: List[Dict]) -> list:
        """Process and standardize a list of Polymarket markets (expects a list of dicts)."""
        return [self.process_polymarket_market(m) for m in polymarket_markets if isinstance(m, dict)]