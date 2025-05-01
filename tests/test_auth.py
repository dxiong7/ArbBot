import unittest
import logging
from cryptography.hazmat.primitives.asymmetric import rsa
from arbbot.kalshi_client import KalshiClient

# Configure logging
logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_kalshi_auth():
    # Generate a test RSA key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Initialize client with mock credentials
    client = KalshiClient("test_key", private_key)
    
    # Test that the client was initialized correctly
    assert client.key_id == "test_key"
    assert client.private_key == private_key

if __name__ == "__main__":
    test_kalshi_auth()