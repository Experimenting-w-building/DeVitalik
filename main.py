from src.cli import ZerePyCLI
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    cli = ZerePyCLI()
    cli.main_loop()
