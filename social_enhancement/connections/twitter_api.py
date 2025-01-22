import logging
import requests
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from zerepy.connections.base_connection import BaseConnection, Action, ActionParameter
from zerepy.utils.env_utils import set_key

logger = logging.getLogger("social_enhancement.connections.twitter_api")

class TwitterAPIConnection(BaseConnection):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://api.twitter.com/2"
        self.api_key = config.get("api_key")
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

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the TwitterAPI.io API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"TwitterAPI.io error: {response.status_code} - {response.text}")
                return {}
                
            return response.json()
                
        except Exception as e:
            logger.error(f"Error making TwitterAPI.io request: {e}")
            return {}

    def search_tweets(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for tweets using a query"""
        logger.info(f"Searching tweets with query: {query}")
        
        try:
            params = {
                "query": query,
                "max_results": min(limit, 100),  # API limit is 100
                "tweet.fields": "created_at,public_metrics,author_id"
            }
            
            response = self._make_request("tweets/search/recent", params)
            
            if not response or "data" not in response:
                return {"tweets": []}
                
            tweets = response["data"]
            return {
                "tweets": [{
                    "id": tweet["id"],
                    "text": tweet["text"],
                    "created_at": tweet["created_at"],
                    "metrics": tweet.get("public_metrics", {}),
                    "author_id": tweet.get("author_id")
                } for tweet in tweets[:limit]]
            }
            
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return {"tweets": []}

    def get_user_tweets(self, username: str, limit: int = 10) -> Dict[str, Any]:
        """Get tweets from a specific user"""
        logger.info(f"Getting tweets for user: {username}")
        
        try:
            user_info = self.get_user_info(username)
            if not user_info or "id" not in user_info:
                return {"tweets": []}
                
            user_id = user_info["id"]
            params = {
                "max_results": min(limit, 100),
                "tweet.fields": "created_at,public_metrics"
            }
            
            response = self._make_request(f"users/{user_id}/tweets", params)
            
            if not response or "data" not in response:
                return {"tweets": []}
                
            tweets = response["data"]
            return {
                "tweets": [{
                    "id": tweet["id"],
                    "text": tweet["text"],
                    "created_at": tweet["created_at"],
                    "metrics": tweet.get("public_metrics", {})
                } for tweet in tweets[:limit]]
            }
            
        except Exception as e:
            logger.error(f"Error getting user tweets: {e}")
            return {"tweets": []}

    def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get information about a Twitter user"""
        logger.info(f"Getting info for user: {username}")
        
        try:
            params = {
                "usernames": username,
                "user.fields": "public_metrics,description,created_at,verified"
            }
            
            response = self._make_request("users/by", params)
            
            if not response or "data" not in response or not response["data"]:
                return {}
                
            user = response["data"][0]
            return {
                "id": user["id"],
                "name": user["name"],
                "username": user["username"],
                "description": user.get("description"),
                "created_at": user.get("created_at"),
                "verified": user.get("verified", False),
                "metrics": user.get("public_metrics", {})
            }
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}

    def configure(self) -> bool:
        """Configure TwitterAPI connection"""
        print("\n🐦 TWITTER API SETUP")
        
        if self.is_configured():
            print("\nTwitterAPI is already configured.")
            response = input("Do you want to reconfigure? (y/n): ")
            if response.lower() != 'y':
                return True

        print("\n📝 To get your TwitterAPI credentials:")
        print("1. Go to https://developer.twitter.com/en/portal/dashboard")
        print("2. Create a new project and app")
        print("3. Get your API key")
        
        api_key = input("\nEnter your TwitterAPI key: ")

        try:
            if not os.path.exists('.env'):
                with open('.env', 'w') as f:
                    f.write('')

            set_key('.env', 'TWITTER_API_KEY', api_key)
            
            # Test the API key
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=headers
            )
            
            if response.status_code != 200:
                raise ValueError(f"Invalid API key: {response.text}")

            print("\n✅ TwitterAPI configuration successfully saved!")
            print("Your API key has been stored in the .env file.")
            return True

        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            return False

    def is_configured(self, verbose = False) -> bool:
        """Check if TwitterAPI is configured and working"""
        try:
            load_dotenv()
            api_key = os.getenv('TWITTER_API_KEY')
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            if verbose:
                logger.error(f"Configuration check failed: {e}")
            return False 