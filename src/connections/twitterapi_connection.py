import logging
import requests
from typing import Dict, Any, List
from src.connections.base_connection import BaseConnection, Action, ActionParameter
import os
from dotenv import load_dotenv, set_key

logger = logging.getLogger("connections.twitterapi_connection")

class TwitterAPIConnection(BaseConnection):
    def __init__(self, config: Dict[str, Any]):
        logger.debug(f"Initializing TwitterAPI connection with config: {config}")
        super().__init__(config)
        self.base_url = "https://api.twitter.com/2"
        self.api_key = config.get("api_key")
        logger.debug(f"Using API key from config: {self.api_key[:10]}...")
        if not self.api_key:
            raise ValueError("TwitterAPI.io API key is required")

    @property
    def is_llm_provider(self) -> bool:
        return False

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate TwitterAPI.io configuration"""
        required_fields = ["api_key"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        return config

    def register_actions(self) -> None:
        """Register available TwitterAPI.io actions"""
        self.actions = {
            "search-tweets": Action(
                name="search-tweets",
                parameters=[
                    ActionParameter("query", True, str, "Search query for tweets"),
                    ActionParameter("limit", False, int, "Maximum number of tweets to return (default: 10)")
                ],
                description="Search for tweets using a query"
            ),
            "get-user-tweets": Action(
                name="get-user-tweets",
                parameters=[
                    ActionParameter("username", True, str, "Twitter username without @"),
                    ActionParameter("limit", False, int, "Maximum number of tweets to return (default: 10)")
                ],
                description="Get tweets from a specific user"
            ),
            "get-user-info": Action(
                name="get-user-info",
                parameters=[
                    ActionParameter("username", True, str, "Twitter username without @")
                ],
                description="Get information about a Twitter user"
            )
        }

    def is_configured(self, verbose: bool = False) -> bool:
        """Check if TwitterAPI is configured and working"""
        try:
            load_dotenv()
            api_key = os.getenv('TWITTER_API_KEY')
            if not api_key:
                if verbose:
                    logger.warning("Twitter API key not found in environment variables")
                return False

            # Test the API key with a simple search query
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Use a simple search query to test the API key
            params = {
                "query": "test",
                "max_results": 1
            }
            
            response = requests.get(
                f"{self.base_url}/tweets/search/recent",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                if verbose:
                    logger.warning(f"Twitter API key validation failed: {response.text}")
                return False
                
            return True
            
        except Exception as e:
            if verbose:
                logger.error(f"Error checking Twitter configuration: {e}")
            return False

    def configure(self) -> bool:
        """Configure TwitterAPI connection"""
        logger.info("\n🐦 TWITTER API SETUP")
        
        if self.is_configured():
            logger.info("\nTwitterAPI is already configured.")
            reconfigure = input("Do you want to reconfigure? (y/n): ")
            if reconfigure.lower() != 'y':
                return True

        logger.info("\n📝 To get your TwitterAPI credentials:")
        logger.info("1. Go to https://developer.twitter.com/en/portal/dashboard")
        logger.info("2. Create a new project and app")
        logger.info("3. Get your API key (Bearer token)")
        
        api_key = input("\nEnter your TwitterAPI key: ")

        try:
            if not os.path.exists('.env'):
                with open('.env', 'w') as f:
                    f.write('')

            set_key('.env', 'TWITTER_API_KEY', api_key)
            
            # Test the API key with a simple search query
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "query": "test",
                "max_results": 1
            }
            
            response = requests.get(
                f"{self.base_url}/tweets/search/recent",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                raise ValueError(f"Invalid API key: {response.text}")

            logger.info("\n✅ TwitterAPI configuration successfully saved!")
            logger.info("Your API key has been stored in the .env file.")
            return True

        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            return False 