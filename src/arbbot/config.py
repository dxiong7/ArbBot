import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Load environment variables
load_dotenv()

# Default Configuration Values
DEFAULT_CONFIG = {
    'INTERNAL_ONLY_MODE': 'False',
    # API Configuration
    'KALSHI_API_KEY': '',
    'POLYMARKET_PRIVATE_KEY': '',
    'POLYMARKET_API_KEY': '',
    
    # Application Settings
    'CHECK_INTERVAL': '300',  # 5 minutes
    'SIMILARITY_THRESHOLD': '0.8',
    'MIN_PROFIT_THRESHOLD': '0.01',  # 1% minimum profit
    
    # Logging Configuration
    'LOG_LEVEL': 'INFO',
    'LOG_FILE': 'arbitrage_bot.log',
    'ARBITRAGE_OUTPUT_FILE': 'arbitrage_opportunities.json',
    
    # API Endpoints
    'KALSHI_BASE_URL': 'https://api.elections.kalshi.com',
    'POLYMARKET_HOST': 'https://clob.polymarket.com'
}

def load_kalshi_private_key() -> rsa.RSAPrivateKey:
    """Load the Kalshi private key from PEM file. Returns None if the file doesn't exist."""
    try:
        with open('kalshi_private_key.pem', 'rb') as key_file:
            return serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )
    except FileNotFoundError:
        return None
    except Exception as e:
        raise ValueError(f"Failed to load Kalshi private key: {str(e)}")

# Get configuration values, using environment variables if available, otherwise defaults
def get_config(key: str) -> str:
    """Get configuration value, preferring environment variables over defaults."""
    return os.getenv(key, DEFAULT_CONFIG.get(key, ''))

# Internal-only mode for Kalshi arbitrage
INTERNAL_ONLY_MODE = get_config('INTERNAL_ONLY_MODE').lower() == 'true'

# API Configuration
KALSHI_API_KEY = get_config('KALSHI_API_KEY')
KALSHI_PRIVATE_KEY = load_kalshi_private_key()
POLYMARKET_PRIVATE_KEY = get_config('POLYMARKET_PRIVATE_KEY').strip("'").strip('"')
POLYMARKET_API_KEY = get_config('POLYMARKET_API_KEY')

# Application Settings
CHECK_INTERVAL = int(get_config('CHECK_INTERVAL'))
SIMILARITY_THRESHOLD = float(get_config('SIMILARITY_THRESHOLD'))
MIN_PROFIT_THRESHOLD = float(get_config('MIN_PROFIT_THRESHOLD'))

# Logging Configuration
LOG_LEVEL = get_config('LOG_LEVEL')
LOG_FILE = get_config('LOG_FILE')
ARBITRAGE_OUTPUT_FILE = get_config('ARBITRAGE_OUTPUT_FILE')

# API Endpoints
KALSHI_BASE_URL = get_config('KALSHI_BASE_URL')
POLYMARKET_HOST = get_config('POLYMARKET_HOST')