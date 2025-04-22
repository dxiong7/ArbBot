import os
import logging
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from main import ArbitrageBot
from config_ui import setup_configuration
from config import (
    KALSHI_API_KEY, POLYMARKET_API_KEY,
    CHECK_INTERVAL, SIMILARITY_THRESHOLD, MIN_PROFIT_THRESHOLD,
    LOG_LEVEL, LOG_FILE
)

console = Console()

# Default Configuration Values
DEFAULT_CONFIG = {
    # API Configuration
    'KALSHI_API_KEY': '',
    'POLYMARKET_API_KEY': '',
    
    # Application Settings
    'CHECK_INTERVAL': '300',  # 5 minutes
    'SIMILARITY_THRESHOLD': '0.8',
    'MIN_PROFIT_THRESHOLD': '0.01',  # 1% minimum profit
    
    # Logging Configuration
    'LOG_LEVEL': 'INFO',
    'LOG_FILE': 'arbitrage_bot.log'
}

def check_configuration() -> bool:
    """Check if all required configuration variables are set."""
    required_vars = [
        'KALSHI_API_KEY',
        'POLYMARKET_API_KEY',
        'CHECK_INTERVAL',
        'SIMILARITY_THRESHOLD',
        'MIN_PROFIT_THRESHOLD',
        'LOG_LEVEL',
        'LOG_FILE'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) and not DEFAULT_CONFIG[var]:
            missing_vars.append(var)
    
    if missing_vars:
        console.print(Panel(
            f"Missing required configuration variables: {', '.join(missing_vars)}\n"
            "Please set these variables in your .env file.",
            style="red"
        ))
        return False
    
    return True

def main():
    """Main entry point for the application."""
    try:
        # Check if configuration exists
        if not check_configuration():
            setup_configuration()
            
        # Start the arbitrage bot
        console.print(Panel("Starting Arbitrage Bot...", style="bold blue"))
        bot = ArbitrageBot()
        bot.run()
        
    except KeyboardInterrupt:
        console.print(Panel("Shutting down Arbitrage Bot...", style="bold red"))
    except Exception as e:
        console.print(Panel(f"Error: {str(e)}", style="red"))
        logging.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main() 