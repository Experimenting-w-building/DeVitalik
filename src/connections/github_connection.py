import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import aiohttp
from dotenv import load_dotenv
from pathlib import Path
from src.connections.base_connection import BaseConnection, Action, ActionParameter
from src.action_handler import register_action

logger = logging.getLogger("github_connection")

class GitHubConnection(BaseConnection):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Try loading from different locations
        load_dotenv()  # Try current directory
        load_dotenv(Path('../.env'))  # Try parent directory
        load_dotenv(Path('../../.env'))  # Try two levels up
        
        self.token = os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GitHub token not found in environment variables")
            
        self.repo = config.get('repository')
        if not self.repo:
            raise ValueError("GitHub repository not specified in config")
            
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
        self.session = None
        self.stats_cache = {}
        self.last_update = None

    @property
    def is_llm_provider(self) -> bool:
        """Whether this connection provides LLM capabilities"""
        return False

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate GitHub configuration"""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        required_fields = ["repository"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")

        return config

    def is_configured(self, verbose: bool = False) -> bool:
        """Check if GitHub connection is properly configured"""
        try:
            if not self.token:
                if verbose:
                    logger.warning("GitHub token not found in environment variables")
                return False
            if not self.repo:
                if verbose:
                    logger.warning("GitHub repository not specified in config")
                return False
            return True
        except Exception as e:
            if verbose:
                logger.error(f"Error checking GitHub configuration: {e}")
            return False

    def configure(self) -> bool:
        """Configure GitHub connection interactively"""
        logger.info("\n🔧 GITHUB CONNECTION SETUP")
        logger.info("\nTo configure GitHub access:")
        logger.info("1. Go to https://github.com/settings/tokens")
        logger.info("2. Generate a new token with 'repo' scope")
        logger.info("3. Add to your .env file: GITHUB_TOKEN=your_token")
        logger.info("4. Specify repository in config: repository=owner/repo")

        try:
            if self.is_configured(verbose=True):
                logger.info("\n✅ GitHub connection is already configured")
                reconfigure = input("Do you want to reconfigure? (y/n): ")
                if reconfigure.lower() != 'y':
                    return True

            token = input("\nEnter your GitHub token: ").strip()
            repo = input("Enter repository (owner/repo format): ").strip()

            if not token or not repo:
                logger.error("Token and repository are required")
                return False

            # Save to .env file
            dotenv_path = Path('.env')
            set_key(dotenv_path, 'GITHUB_TOKEN', token)
            
            # Update instance
            self.token = token
            self.repo = repo
            self.headers['Authorization'] = f'token {token}'

            logger.info("\n✅ GitHub connection configured successfully")
            return True

        except Exception as e:
            logger.error(f"Error configuring GitHub connection: {e}")
            return False

    def register_actions(self) -> None:
        """Register available GitHub actions"""
        self.actions = {
            "get-repository-stats": Action(
                name="get-repository-stats",
                parameters=[],
                description="Get repository statistics including stars, forks, issues, and recent activity"
            )
        }

    async def setup(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    @register_action("get-repository-stats")
    async def get_repository_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        logger.info(f"Fetching fresh stats for repository: {self.repo}")
        
        try:
            # Get repository info
            logger.info("Fetching repository info...")
            repo_info = await self._make_request(f"repos/{self.repo}")
            
            # Get recent stargazers
            logger.info("Fetching recent stargazers...")
            recent_stars = await self._get_recent_stars()
            
            # Get recent commits
            logger.info("Fetching recent commits...")
            recent_commits = await self._get_recent_commits()
            
            # Get open PRs
            logger.info("Fetching open PRs...")
            open_prs = await self._make_request(f"repos/{self.repo}/pulls?state=open")
            
            # Calculate real star change
            current_stars = repo_info.get("stargazers_count", 0)
            new_stars = len(recent_stars) if recent_stars else 0
            
            # Validate star count against previous state
            if hasattr(self, '_last_star_count'):
                star_diff = current_stars - self._last_star_count
                if star_diff < new_stars:
                    # If the actual difference is less than reported new stars,
                    # use the actual difference
                    new_stars = max(0, star_diff)
            
            # Store current star count for next comparison
            self._last_star_count = current_stars
            
            # Only include new stars section if we actually have new stars
            stats = {
                "stars": current_stars,
                "forks": repo_info.get("forks_count", 0),
                "open_issues": repo_info.get("open_issues_count", 0),
                "recent_commits": len(recent_commits) if recent_commits else 0,
                "open_prs": len(open_prs) if open_prs else 0,
                "watchers": repo_info.get("subscribers_count", 0)
            }
            
            if new_stars > 0:
                stats["new_stars"] = new_stars
            
            logger.info(f"Collected GitHub stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching repository stats: {e}")
            return {}

    async def _get_recent_stars(self) -> List[Dict[str, Any]]:
        """Get stars from the last 24 hours"""
        try:
            all_stars = []
            page = 1
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            
            while True:
                # Get stargazers with timestamps, paginated
                stars = await self._make_request(
                    f"repos/{self.repo}/stargazers",
                    params={"page": page, "per_page": 100},
                    headers={"Accept": "application/vnd.github.star+json"}
                )
                
                if not stars:
                    break
                    
                # Filter to last 24 hours
                recent_stars = [
                    star for star in stars
                    if datetime.fromisoformat(star.get("starred_at", "").replace("Z", "+00:00")) > cutoff
                ]
                
                # If we've gone past the 24 hour window, stop paginating
                if len(recent_stars) < len(stars):
                    all_stars.extend(recent_stars)
                    break
                    
                all_stars.extend(recent_stars)
                
                # If we got less than requested, we've hit the end
                if len(stars) < 100:
                    break
                    
                page += 1
            
            return all_stars
            
        except Exception as e:
            logger.error(f"Error fetching recent stars: {e}")
            return []
            
    async def _get_recent_commits(self) -> List[Dict[str, Any]]:
        """Get commits from the last 24 hours"""
        try:
            # Get recent commits
            since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            commits = await self._make_request(
                f"repos/{self.repo}/commits",
                params={"since": since}
            )
            
            return commits if commits else []
            
        except Exception as e:
            logger.error(f"Error fetching recent commits: {e}")
            return []

    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make a request to the GitHub API"""
        try:
            if not self.session:
                await self.setup()
                
            merged_headers = {**self.headers}
            if headers:
                merged_headers.update(headers)
                
            async with self.session.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                headers=merged_headers
            ) as response:
                if response.status == 401:
                    logger.error("GitHub authentication failed. Check your token.")
                    return {}
                elif response.status == 403:
                    logger.error("GitHub API rate limit exceeded or access denied.")
                    return {}
                elif response.status != 200:
                    logger.error(f"Failed to fetch {endpoint}: {response.status}")
                    logger.error(f"Response: {await response.text()}")
                    return {}
                    
                return await response.json()
                
        except Exception as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            return {} 