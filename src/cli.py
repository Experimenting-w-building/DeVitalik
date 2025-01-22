import sys
import json
import logging
import os
from dataclasses import dataclass
from typing import Callable, Dict, List
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from src.agent import ZerePyAgent
from src.helpers import print_h_bar
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("cli")

@dataclass
class Command:
    """Dataclass to represent a CLI command"""
    name: str
    description: str
    tips: List[str]
    handler: Callable
    aliases: List[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []

class ZerePyCLI:
    def __init__(self):
        self.agent = ZerePyAgent()

    def main_loop(self):
        """Start the main agent loop"""
        try:
            asyncio.run(self.agent.loop())
            return True
        except KeyboardInterrupt:
            logger.info("\n🛑 Agent loop stopped by user.")
            return True
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            return False 