import logging
import json
from typing import Dict, Any, List
import math
import numpy as np
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("social_enhancement.processors.task_processor")

class TaskProcessor:
    def __init__(self):
        """Initialize task processor"""
        self.logger = logger

    async def process_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process a social enhancement task"""
        try:
            results = {}
            
            # Process based on task type
            if task_config.get('name') == 'crypto_social_pulse':
                results = await self._process_social_pulse(task_config)
            elif task_config.get('name') == 'track_influencer_activity':
                results = await self._process_influencer_tracking(task_config)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            return {}

    async def _process_social_pulse(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process crypto social pulse task"""
        return {
            'status': 'processed',
            'task': 'social_pulse',
            'timestamp': str(datetime.now())
        }

    async def _process_influencer_tracking(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process influencer tracking task"""
        return {
            'status': 'processed',
            'task': 'influencer_tracking',
            'timestamp': str(datetime.now())
        }

    async def _handle_twitter_action(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Twitter-specific actions using the collector"""
        if action_type == "search-tweets":
            return await self.twitter_collector.search_tweets_parallel(
                params.get("query", ""),
                params.get("limit", 10)
            )
        elif action_type == "get-user-tweets":
            return await self.twitter_collector.monitor_user_activity(
                params.get("username", ""),
                params.get("limit", 10)
            )
        return {}

    def _process_templates(self, params: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Process template variables in parameters"""
        processed = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                template_var = value[2:-2].strip()
                if template_var in results:
                    processed[key] = results[template_var]
                elif "." in template_var:
                    # Handle nested template variables
                    parts = template_var.split(".")
                    current = results
                    for part in parts:
                        if isinstance(current, dict):
                            current = current.get(part, {})
                        else:
                            current = {}
                    processed[key] = current
            else:
                processed[key] = value
        return processed

    async def _handle_post_processing(self, config: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Handle post-processing of task results"""
        analysis = {}

        if config.get("combine_data"):
            analysis["combined_data"] = self._combine_social_data(results)

        if config.get("calculate_sentiment"):
            analysis["sentiment"] = await self._calculate_sentiment(results)

        if config.get("correlation_analysis"):
            analysis["correlations"] = self._analyze_correlations(
                results,
                config["correlation_analysis"]
            )

        return analysis

    async def _handle_notifications(self, config: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Handle task notifications"""
        if not self._should_notify(config, results):
            return

        notification = self._prepare_notification(results)
        
        if config.get("telegram"):
            # Send to Telegram
            pass
            
        if config.get("discord"):
            # Send to Discord
            pass

    def _should_notify(self, config: Dict[str, Any], results: Dict[str, Any]) -> bool:
        """Check if notification conditions are met"""
        conditions = config.get("conditions", {})
        
        if "min_confidence" in conditions:
            confidence = results.get("analysis", {}).get("confidence", 0)
            if confidence < conditions["min_confidence"]:
                return False
                
        return True

    def _prepare_notification(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare notification content"""
        return {
            "summary": self._generate_summary(results),
            "details": results.get("analysis", {}),
            "timestamp": results.get("timestamp")
        }

    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a summary of the results"""
        analysis = results.get("analysis", {})
        
        if "sentiment" in analysis:
            return f"Sentiment Analysis: {analysis['sentiment']:.2f}"
            
        return "Task completed successfully"

    def _combine_social_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Combine data from different social sources"""
        combined = {
            'tweets': [],
            'casts': [],
            'metrics': defaultdict(float),
            'mentions': defaultdict(int)
        }
        
        # Combine Twitter data
        if 'fetch_twitter_data' in results:
            combined['tweets'].extend(results['fetch_twitter_data'].get('tweets', []))
            
        if 'fetch_influencer_data' in results:
            combined['tweets'].extend(results['fetch_influencer_data'].get('tweets', []))
            
        # Combine Farcaster data
        if 'fetch_farcaster_data' in results:
            combined['casts'].extend(results['fetch_farcaster_data'].get('casts', []))
            
        # Extract metrics and mentions
        for tweet in combined['tweets']:
            metrics = tweet.get('public_metrics', {})
            combined['metrics']['likes'] += metrics.get('like_count', 0)
            combined['metrics']['retweets'] += metrics.get('retweet_count', 0)
            combined['metrics']['replies'] += metrics.get('reply_count', 0)
            
            # Count token mentions
            text = tweet.get('text', '').lower()
            for token in ['$eth', '$btc', '$sol', '$matic']:
                if token in text:
                    combined['mentions'][token] += 1
                    
        return combined

    async def _calculate_sentiment(self, results: Dict[str, Any]) -> float:
        """Calculate overall sentiment from social data"""
        if not results:
            return 0.0
            
        combined_data = self._combine_social_data(results)
        total_score = 0
        total_items = 0
        
        # Simple keyword-based sentiment
        positive = ['bullish', 'moon', 'pump', 'good', 'great', 'excited']
        negative = ['bearish', 'dump', 'bad', 'rekt', 'down']
        
        for tweet in combined_data['tweets']:
            text = tweet.get('text', '').lower()
            score = 0
            
            for word in text.split():
                if word in positive:
                    score += 1
                elif word in negative:
                    score -= 1
                    
            # Weight by engagement
            metrics = tweet.get('public_metrics', {})
            engagement = (
                metrics.get('like_count', 0) +
                metrics.get('retweet_count', 0) * 2 +
                metrics.get('reply_count', 0) * 1.5
            )
            
            if engagement > 0:
                weighted_score = score * (1 + math.log(engagement + 1))
                total_score += weighted_score
                total_items += 1
                
        return total_score / max(total_items, 1)

    def _analyze_correlations(self, results: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze correlations between different metrics"""
        timeframe = config.get('timeframe', '1h')
        metrics = config.get('metrics', [])
        
        if not metrics or not results:
            return {}
            
        correlations = {}
        combined_data = self._combine_social_data(results)
        
        # Calculate basic correlations
        if 'price' in metrics and 'social_engagement' in metrics:
            # Simple correlation between price movement and social engagement
            price_changes = []
            engagements = []
            
            for token, market_data in results.get('analyze_market_data', {}).items():
                if 'price_change_24h' in market_data:
                    price_changes.append(market_data['price_change_24h'])
                    
                    # Get corresponding social engagement
                    token_engagement = (
                        combined_data['metrics'].get('likes', 0) +
                        combined_data['metrics'].get('retweets', 0) * 2
                    )
                    engagements.append(token_engagement)
                    
            if price_changes and engagements:
                correlations['price_social'] = np.corrcoef(price_changes, engagements)[0, 1]
                
        return correlations 