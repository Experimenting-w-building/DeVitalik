from typing import Optional, Dict, Any, List
import logging
import json
import os
from sentence_transformers import SentenceTransformer
from zerepy.core import BaseAgent
from .analyzers.content_analyzer import ContentAnalyzer
from .connections.twitter_api import TwitterAPIConnection
from .processors.task_processor import TaskProcessor

logger = logging.getLogger("social_enhancement.social_manager")

class SocialManager:
    """
    Manages social interactions while keeping core ZerePy functionality intact
    Acts as a bridge between your custom social logic and ZerePy's core
    """
    
    def __init__(self, agent: BaseAgent):
        self.agent = agent
        self._interaction_history = {}
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.content_analyzer = ContentAnalyzer(self.embedding_model)
        self.task_processor = TaskProcessor(agent.connection_manager)
        
        # Load configurations
        self.configs = self._load_configs()
        
    def _load_configs(self) -> Dict[str, Any]:
        """Load all configuration files"""
        config_dir = os.path.join(os.path.dirname(__file__), 'config')
        configs = {}
        
        for filename in os.listdir(config_dir):
            if filename.endswith('.json'):
                with open(os.path.join(config_dir, filename)) as f:
                    configs[filename[:-5]] = json.load(f)
                    
        return configs
        
    def enhance_agent(self):
        """
        Enhances the agent with social capabilities without modifying core functionality
        """
        # Attach social methods to agent instance without modifying the class
        self.agent.social = self
        
        # Register social connections if not already present
        self._register_social_connections()
        
    def _register_social_connections(self):
        """Register social-specific connections"""
        if 'twitterapi' not in self.agent.connection_manager.connections:
            self.agent.connection_manager.register_connection(
                'twitterapi',
                TwitterAPIConnection({
                    'api_key': os.getenv('TWITTER_API_KEY')
                })
            )
            
    async def handle_interaction(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Main entry point for social interactions
        """
        try:
            # Process market context
            market_context = await self.content_analyzer.analyze_market_context(
                self.agent.connection_manager.connections.get('dexscreener')
            )
            
            # Process social context
            social_context = await self.content_analyzer.analyze_social_context(
                self.agent.connection_manager.connections.get('twitter'),
                self.agent.connection_manager.connections.get('twitterapi')
            )
            
            # Generate content ideas
            content_ideas = self.content_analyzer.generate_content_ideas(
                market_context,
                social_context
            )
            
            # Process tasks based on context
            for task_name, task_config in self.configs.items():
                if task_config.get('enabled', True):
                    await self.task_processor.process_task(task_config)
            
            # Store interaction history
            self._interaction_history[context.get('id')] = {
                'market_context': market_context,
                'social_context': social_context,
                'content_ideas': content_ideas
            }
            
            # Generate response if needed
            if content_ideas:
                return self.content_analyzer.format_content_prompt(content_ideas[0])
                
        except Exception as e:
            logger.error(f"Error handling interaction: {e}")
            
        return None
        
    async def get_interaction_history(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Get historical interaction data"""
        return self._interaction_history.get(interaction_id) 