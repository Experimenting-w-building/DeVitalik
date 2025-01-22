import json
import random
import time
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from src.connection_manager import ConnectionManager
from src.helpers import print_h_bar
from src.action_handler import execute_action
from social_enhancement.social_manager import SocialManager
import src.actions.twitter_actions  
import src.actions.echochamber_actions
import src.actions.solana_actions
from datetime import datetime
from typing import Optional, Dict, Any

REQUIRED_FIELDS = ["name", "bio", "traits", "examples", "loop_delay", "config", "tasks"]

logger = logging.getLogger("zerepy.agent")

class ZerePyAgent:
    def __init__(self, agent_name: str = "devitalik"):
        """Initialize ZerePy agent with configuration"""
        self.agent_name = agent_name
        self.agent_config = self._load_config()
        self.logger = logger  # Use the module-level logger
        # Initialize connection manager with just the connections config
        self.connection_manager = ConnectionManager(self.agent_config.get("config", []))
        self.social = SocialManager(self)
        self.state = {}
        self._system_prompt = None
        self.is_llm_set = False
        
    @property
    def name(self) -> str:
        """Get the agent's name"""
        return self.agent_name
        
    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration from JSON file"""
        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "agents",
            f"{self.agent_name}.json"
        )
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load agent config: {e}")
            return {}

    def _setup_llm_provider(self):
        # Get first available LLM provider and its model
        llm_providers = self.connection_manager.get_model_providers()
        if not llm_providers:
            raise ValueError("No configured LLM provider found")
        self.model_provider = llm_providers[0]

        # Load Twitter username for self-reply detection if Twitter tasks exist
        if any("tweet" in task["name"] for task in self.agent_config.get("tasks", [])):
            load_dotenv()
            self.username = os.getenv('TWITTER_USERNAME', '').lower()
            if not self.username:
                logger.warning("Twitter username not found, some Twitter functionalities may be limited")

    def _construct_system_prompt(self) -> str:
        """Construct the system prompt from agent configuration"""
        if self._system_prompt is None:
            prompt_parts = []
            prompt_parts.append("Focus on technical insights about blockchain development, protocol design, and ecosystem trends.")
            prompt_parts.append("Analyze patterns, optimizations, and architectural decisions.")
            prompt_parts.append("Maintain a professional, analytical tone.")
            prompt_parts.append("Do not use first or third person - focus on the technical observations themselves.")

            if self.agent_config.get("traits"):
                prompt_parts.append("\nKey areas of focus:")
                prompt_parts.extend(f"- {trait}" for trait in self.agent_config["traits"])

            if self.agent_config.get("examples"):
                prompt_parts.append("\nStyle examples (for reference, do not repeat):")
                prompt_parts.extend(f"- {example}" for example in self.agent_config["examples"])

            self._system_prompt = "\n".join(prompt_parts)

        return self._system_prompt
    
    def _adjust_weights_for_time(self, current_hour: int, task_weights: list) -> list:
        """Adjust task weights based on time of day"""
        weights = task_weights.copy()
        tasks = self.agent_config.get("tasks", [])
        multipliers = self.agent_config.get("time_based_multipliers", {})
        
        # Reduce tweet frequency during night hours (1 AM - 5 AM)
        if 1 <= current_hour <= 5:
            weights = [
                weight * multipliers.get("tweet_night_multiplier", 0.4) 
                if task.get("name") == "post-tweet" else weight
                for weight, task in zip(weights, tasks)
            ]
            
        # Increase engagement frequency during day hours (8 AM - 8 PM)
        if 8 <= current_hour <= 20:
            weights = [
                weight * multipliers.get("engagement_day_multiplier", 1.5)
                if task.get("name") in ("reply-to-tweet", "like-tweet") else weight
                for weight, task in zip(weights, tasks)
            ]
        
        return weights

    def prompt_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text using the configured LLM provider"""
        system_prompt = system_prompt or self._construct_system_prompt()

        return self.connection_manager.perform_action(
            connection_name=self.model_provider,
            action_name="generate-text",
            params=[prompt, system_prompt]
        )

    def perform_action(self, connection: str, action: str, **kwargs) -> None:
        return self.connection_manager.perform_action(connection, action, **kwargs)
    
    def select_action(self, use_time_based_weights: bool = False) -> dict:
        """Select an action based on task weights"""
        tasks = self.agent_config.get("tasks", [])
        if not tasks:
            logger.warning("No tasks configured")
            return {}
            
        # Extract weights from tasks
        task_weights = [task.get("weight", 1) for task in tasks]
        
        if use_time_based_weights:
            current_hour = datetime.now().hour
            task_weights = self._adjust_weights_for_time(current_hour, task_weights)
        
        return random.choices(tasks, weights=task_weights, k=1)[0]

    async def loop(self):
        """Main agent loop for autonomous behavior"""
        if not self.is_llm_set:
            self._setup_llm_provider()

        logger.info("\n🚀 Starting agent loop...")
        logger.info("Press Ctrl+C at any time to stop the loop.")
        print_h_bar()

        time.sleep(2)
        logger.info("Starting loop in 5 seconds...")
        for i in range(5, 0, -1):
            logger.info(f"{i}...")
            time.sleep(1)

        try:
            while True:
                success = False
                try:
                    # REPLENISH INPUTS
                    if "timeline_tweets" not in self.state or self.state["timeline_tweets"] is None or len(self.state["timeline_tweets"]) == 0:
                        if any("tweet" in task["name"] for task in self.agent_config.get("tasks", [])):
                            logger.info("\n👀 READING TIMELINE")
                            timeline = self.connection_manager.perform_action(
                                connection_name="twitter",
                                action_name="read-timeline",
                                params=[]
                            )
                            
                            # Store timeline in both state and Twitter connection
                            self.state["timeline_tweets"] = timeline
                            twitter_conn = self.connection_manager.connections.get('twitter')
                            if twitter_conn:
                                twitter_conn.timeline = timeline
                            
                            # Process timeline with social enhancements
                            if timeline:
                                logger.info("\n🔍 ANALYZING SOCIAL CONTEXT")
                                social_context = await self.social.analyze_social_context(
                                    self.connection_manager.connections.get('twitter'),
                                    self.connection_manager.connections.get('twitterapi')
                                )
                                self.state["social_context"] = social_context
                                logger.info("\n📊 ANALYZING MARKET CONTEXT")
                                market_context = await self.social.analyze_market_context(
                                    self.connection_manager.connections.get('dexscreener')
                                )
                                self.state["market_context"] = market_context

                    if "room_info" not in self.state or self.state["room_info"] is None:
                        if any("echochambers" in task["name"] for task in self.agent_config["tasks"]):
                            logger.info("\n👀 READING ECHOCHAMBERS ROOM INFO")
                            self.state["room_info"] = self.connection_manager.perform_action(
                                connection_name="echochambers",
                                action_name="get-room-info",
                                params={}
                            )

                    # CHOOSE AN ACTION
                    action = self.select_action(use_time_based_weights=self.agent_config.get("use_time_based_weights", False))
                    action_name = action["name"]

                    # PERFORM ACTION
                    success = execute_action(self, action_name)

                    logger.info(f"\n⏳ Waiting {self.agent_config['loop_delay']} seconds before next loop...")
                    time.sleep(self.agent_config['loop_delay'])

                except Exception as e:
                    logger.error(f"Error in agent loop: {e}")
                    time.sleep(self.agent_config['loop_delay'])

        except KeyboardInterrupt:
            logger.info("\n👋 Stopping agent loop...")
            return