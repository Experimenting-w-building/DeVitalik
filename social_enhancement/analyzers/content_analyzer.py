import logging
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from typing import Dict, Any, List
from datetime import datetime
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform color support
colorama.init()

logger = logging.getLogger("social_enhancement.analyzers.content_analyzer")

class ContentAnalyzer:
    def __init__(self):
        """Initialize the content analyzer"""
        self.context_cache = {}
        self.sia = SentimentIntensityAnalyzer()
        self.priority_topics = {
            'ai': ['agent', 'automation', 'bot', 'gpt', 'llm', 'claude', 'ai'],
            'blockchain': ['blockchain', 'web3', 'crypto', 'protocol', 'chain'],
            'defi': ['defi', 'defai', 'trading', 'dex', 'amm', 'liquidity'],
            'development': ['zerepy', 'python', 'sdk', 'api', 'developer', 'code'],
            'optimization': ['gas', 'efficiency', 'performance', 'scaling', 'optimization']
        }
        
    def print_status(self, message: str, status: str = "info"):
        """Print a colorful status message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = Fore.WHITE
        icon = "💡"
        
        if status == "success":
            color = Fore.GREEN
            icon = "✅"
        elif status == "error":
            color = Fore.RED
            icon = "❌"
        elif status == "warning":
            color = Fore.YELLOW
            icon = "⚠️"
        elif status == "highlight":
            color = Fore.CYAN
            icon = "🔍"
            
        print(f"[{timestamp}] {color}{icon} {message}{Style.RESET_ALL}")

    def _calculate_engagement_potential(self, tweet: Dict[str, Any], topic_matches: List[str]) -> float:
        """Calculate potential engagement score for a tweet"""
        metrics = tweet.get('public_metrics', {})
        
        # Base engagement metrics
        likes = metrics.get('like_count', 0)
        retweets = metrics.get('retweet_count', 0)
        replies = metrics.get('reply_count', 0)
        quotes = metrics.get('quote_count', 0)
        
        # Calculate base score with weighted metrics
        base_score = (
            likes * 1.0 +      # Each like is worth 1 point
            retweets * 2.0 +   # Retweets worth 2 points (more visibility)
            replies * 1.5 +    # Replies worth 1.5 points (shows discussion)
            quotes * 2.5       # Quotes worth 2.5 points (shows viral potential)
        )
        
        # Boost score for priority topics (20% boost per matched topic)
        topic_boost = sum(0.2 for topic in topic_matches if any(
            topic in keywords for keywords in self.priority_topics.values()
        ))
        
        # Consider tweet recency (use UTC for consistency)
        try:
            created_at = datetime.fromisoformat(tweet.get('created_at', datetime.utcnow().isoformat()).replace('Z', '+00:00'))
            time_diff = datetime.now(created_at.tzinfo) - created_at
            hours_old = time_diff.total_seconds() / 3600
            
            # Exponential decay based on hours
            # 1.0 for brand new, 0.5 at 12 hours, ~0.25 at 24 hours
            recency_boost = 2 ** (-hours_old / 12)
        except Exception as e:
            self.print_status(f"Error calculating recency: {e}", "warning")
            recency_boost = 0  # Default to no recency boost if date parsing fails
        
        final_score = base_score * (1 + topic_boost) * (1 + recency_boost)
        
        return final_score

    async def analyze_social_context(self, twitter_conn, twitterapi_conn) -> Dict[str, Any]:
        """Analyze social context from timeline tweets"""
        self.print_status("Starting social context analysis...")
        
        try:
            timeline = twitter_conn.timeline if hasattr(twitter_conn, 'timeline') else []
            
            if not timeline:
                self.print_status("No timeline tweets found", "warning")
                return {}
                
            self.print_status(f"Processing {len(timeline)} tweets from timeline", "info")
            
            interesting_discussions = []
            topic_sentiments = {category: [] for category in self.priority_topics}
            
            for tweet in timeline:
                text = tweet.get('text', '').lower()
                author = tweet.get('author_username', 'unknown')
                metrics = tweet.get('public_metrics', {})
                
                self.print_status(f"\nAnalyzing tweet from @{author}:", "info")
                self.print_status(f"Text: {text[:100]}...", "info")
                self.print_status(f"Metrics: {metrics}", "info")
                
                words = word_tokenize(text)
                stop_words = set(stopwords.words('english'))
                meaningful_words = [word for word in words if word.isalnum() and word not in stop_words]
                
                # Find matching priority topics
                topic_matches = []
                for category, keywords in self.priority_topics.items():
                    if any(keyword in meaningful_words for keyword in keywords):
                        topic_matches.append(category)
                        sentiment = self.sia.polarity_scores(text)['compound']
                        topic_sentiments[category].append(sentiment)
                        self.print_status(f"Matched topic: {category} (sentiment: {sentiment:.2f})", "success")
                
                if topic_matches:
                    engagement_score = self._calculate_engagement_potential(tweet, topic_matches)
                    self.print_status(f"Engagement score: {engagement_score:.2f}", "highlight")
                    interesting_discussions.append({
                        'text': text,
                        'author': author,
                        'topics': topic_matches,
                        'engagement_score': engagement_score,
                        'sentiment': self.sia.polarity_scores(text)['compound'],
                        'metrics': metrics
                    })
            
            # Sort by engagement potential
            interesting_discussions.sort(key=lambda x: x['engagement_score'], reverse=True)
            
            # Find the most engaging discussion for content generation
            if interesting_discussions:
                top_discussion = interesting_discussions[0]
                self.print_status("\nMost Engaging Discussion:", "highlight")
                self.print_status(f"Author: @{top_discussion['author']}")
                self.print_status(f"Topics: {', '.join(top_discussion['topics'])}")
                self.print_status(f"Text: {top_discussion['text'][:100]}...")
                self.print_status(f"Engagement Score: {top_discussion['engagement_score']:.1f}")
                self.print_status(f"Metrics: {top_discussion['metrics']}")
                
                # Calculate average sentiment per topic
                topic_insights = {}
                for category, sentiments in topic_sentiments.items():
                    if sentiments:
                        avg_sentiment = sum(sentiments) / len(sentiments)
                        topic_insights[category] = {
                            'sentiment': avg_sentiment,
                            'discussion_count': len(sentiments)
                        }
                        self.print_status(f"{category}: {len(sentiments)} discussions, avg sentiment: {avg_sentiment:.2f}", "info")
                
                return {
                    'top_discussion': top_discussion,
                    'topic_insights': topic_insights,
                    'analyzed_tweets': len(timeline)
                }
            
            return {}
            
        except Exception as e:
            self.print_status(f"Error analyzing social context: {e}", "error")
            return {}

    async def analyze_market_context(self, dexscreener_conn) -> Dict[str, Any]:
        """Simple market context analysis"""
        return {} 