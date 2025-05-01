import os
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from dotenv import load_dotenv, set_key
from py_clob_client.client import ClobClient, ApiCreds
from py_clob_client.constants import POLYGON

console = Console()

def setup_polymarket_auth():
    """Interactive setup for Polymarket authentication."""
    console.print(Panel(
        "Polymarket Authentication Setup",
        style="bold blue"
    ))
    
    # Get user input
    private_key = Prompt.ask("Enter your private key", password=True)
    creds = ApiCreds(
        api_key=os.getenv("POLYMARKET_API_KEY"),
        api_secret=os.getenv("POLYMARKET_API_SECRET"),
        api_passphrase=os.getenv("POLYMARKET_API_PASSPHRASE")
    )
    try:
        # Initialize client
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=POLYGON,
            creds=creds
        )
        
        # Create or derive API credentials
        credentials = client.create_or_derive_api_creds()
        print(credentials)
        # Save credentials
        env_path = ".env"
        set_key(env_path, "POLYMARKET_PRIVATE_KEY", private_key)
        set_key(env_path, "POLYMARKET_API_KEY", credentials.api_key)
        set_key(env_path, "POLYMARKET_API_SECRET", credentials.api_secret)
        set_key(env_path, "POLYMARKET_API_PASSPHRASE", credentials.api_passphrase)
        
        # Derive the address from the private key
        from eth_account import Account
        try:
            account = Account.from_key(private_key)
            address = account.address
        except Exception as e:
            console.print(Panel(f"Failed to derive address from private key: {str(e)}", style="bold red"))
            raise

        # Check access status
        import requests
        try:
            url = f"https://clob.polymarket.com/auth/ban-status/cert-required?address={address}"
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()
            cert_required = data.get("cert_required", None)
            if cert_required is True:
                console.print(Panel(
                    f"Access Status: CERTIFICATE REQUIRED for address {address}\n\nYou may need to complete additional verification steps.",
                    style="bold yellow"
                ))
            elif cert_required is False:
                console.print(Panel(
                    f"Access Status: No certificate required for address {address}. You have normal access.",
                    style="bold green"
                ))
            else:
                console.print(Panel(
                    f"Access Status: Unexpected response for address {address}: {data}",
                    style="bold red"
                ))
        except Exception as e:
            console.print(Panel(f"Failed to check access status: {str(e)}", style="bold red"))
            raise

        console.print(Panel(
            "Authentication setup successful!\n\n"
            "Your private key has been saved securely.",
            style="bold green"
        ))
        
    except Exception as e:
        console.print(Panel(
            f"Authentication failed: {str(e)}",
            style="bold red"
        ))
        raise

if __name__ == "__main__":
    setup_polymarket_auth() 