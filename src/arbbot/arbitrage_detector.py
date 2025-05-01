import pandas as pd
import numpy as np
from typing import List, Dict
import logging
from difflib import SequenceMatcher

class ArbitrageDetector:
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.logger = logging.getLogger(__name__)
        
    def find_similar_markets(self, markets_df: pd.DataFrame) -> List[Dict]:
        """Find similar markets between platforms based on title similarity."""
        try:
            # Split markets by platform
            kalshi_markets = markets_df[markets_df['platform'] == 'kalshi']
            polymarket_markets = markets_df[markets_df['platform'] == 'polymarket']
            
            similar_markets = []
            
            # Compare each Kalshi market with each Polymarket market
            for _, k_market in kalshi_markets.iterrows():
                for _, p_market in polymarket_markets.iterrows():
                    similarity = self._calculate_similarity(
                        k_market['title'],
                        p_market['title']
                    )
                    
                    if similarity >= self.similarity_threshold:
                        similar_markets.append({
                            'kalshi_market': k_market,
                            'polymarket_market': p_market,
                            'similarity': similarity
                        })
                        
            return similar_markets
        except Exception as e:
            self.logger.error(f"Error finding similar markets: {e}")
            raise
            
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using SequenceMatcher."""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
        
    def detect_arbitrage(self, similar_markets: List[Dict]) -> List[Dict]:
        """Detect arbitrage opportunities from similar markets."""
        try:
            opportunities = []
            
            for market_pair in similar_markets:
                k_market = market_pair['kalshi_market']
                p_market = market_pair['polymarket_market']
                
                # Check for arbitrage opportunities in both directions
                # 1. Buy Yes on Kalshi, Buy No on Polymarket
                total_cost_1 = k_market['yes_price'] + p_market['no_price']
                profit_1 = 1.0 - total_cost_1
                
                # 2. Buy No on Kalshi, Buy Yes on Polymarket
                total_cost_2 = k_market['no_price'] + p_market['yes_price']
                profit_2 = 1.0 - total_cost_2
                
                # If either combination yields a profit
                if profit_1 > 0 or profit_2 > 0:
                    opportunity = {
                        'kalshi_market_id': k_market['market_id'],
                        'kalshi_title': k_market['title'],
                        'polymarket_market_id': p_market['market_id'],
                        'polymarket_title': p_market['title'],
                        'similarity': market_pair['similarity'],
                        'kalshi_yes_price': k_market['yes_price'],
                        'kalshi_no_price': k_market['no_price'],
                        'polymarket_yes_price': p_market['yes_price'],
                        'polymarket_no_price': p_market['no_price'],
                        'max_profit': max(profit_1, profit_2),
                        'strategy': 'Buy Yes on Kalshi, Buy No on Polymarket' if profit_1 > profit_2
                                  else 'Buy No on Kalshi, Buy Yes on Polymarket'
                    }
                    opportunities.append(opportunity)
                    
            return opportunities
        except Exception as e:
            self.logger.error(f"Error detecting arbitrage: {e}")
            raise 