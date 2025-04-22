import os
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from dotenv import load_dotenv, set_key

from config import DEFAULT_CONFIG

console = Console()

def setup_configuration():
    """Interactive configuration setup."""
    console.print(Panel("Welcome to the Arbitrage Bot Configuration", style="bold blue"))
    
    # Load existing .env file if it exists
    env_path = ".env"
    load_dotenv(env_path)
    
    # Get current values or use defaults from config.py
    current_email = os.getenv('KALSHI_EMAIL', DEFAULT_CONFIG['KALSHI_EMAIL'])
    current_password = os.getenv('KALSHI_PASSWORD', DEFAULT_CONFIG['KALSHI_PASSWORD'])
    current_api_key = os.getenv('POLYMARKET_API_KEY', DEFAULT_CONFIG['POLYMARKET_API_KEY'])
    current_interval = os.getenv('CHECK_INTERVAL', DEFAULT_CONFIG['CHECK_INTERVAL'])
    current_threshold = os.getenv('SIMILARITY_THRESHOLD', DEFAULT_CONFIG['SIMILARITY_THRESHOLD'])
    current_min_profit = os.getenv('MIN_PROFIT_THRESHOLD', DEFAULT_CONFIG['MIN_PROFIT_THRESHOLD'])
    
    # Collect configuration
    console.print("\n[bold]API Configuration[/bold]")
    kalshi_email = Prompt.ask("Kalshi Email", default=current_email)
    kalshi_password = Prompt.ask("Kalshi Password", default=current_password, password=True)
    polymarket_key = Prompt.ask("Polymarket API Key", default=current_api_key)
    
    console.print("\n[bold]Application Settings[/bold]")
    check_interval = Prompt.ask(
        "Check Interval (seconds)",
        default=current_interval,
        choices=["60", "300", "600", "900"],
        show_choices=True
    )
    similarity_threshold = Prompt.ask(
        "Market Similarity Threshold",
        default=current_threshold,
        choices=["0.7", "0.8", "0.9"],
        show_choices=True
    )
    min_profit = Prompt.ask(
        "Minimum Profit Threshold",
        default=current_min_profit,
        choices=["0.005", "0.01", "0.02", "0.05"],
        show_choices=True
    )
    
    # Save configuration
    set_key(env_path, 'KALSHI_EMAIL', kalshi_email)
    set_key(env_path, 'KALSHI_PASSWORD', kalshi_password)
    set_key(env_path, 'POLYMARKET_API_KEY', polymarket_key)
    set_key(env_path, 'CHECK_INTERVAL', check_interval)
    set_key(env_path, 'SIMILARITY_THRESHOLD', similarity_threshold)
    set_key(env_path, 'MIN_PROFIT_THRESHOLD', min_profit)
    
    console.print(Panel("Configuration saved successfully!", style="bold green"))
    
if __name__ == "__main__":
    setup_configuration() 