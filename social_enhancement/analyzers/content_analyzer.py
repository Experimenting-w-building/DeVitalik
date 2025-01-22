import logging
from typing import Dict, Any, List
from collections import defaultdict
import numpy as np
from datetime import datetime, timedelta
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('sentiment/vader_lexicon')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('vader_lexicon')
    nltk.download('stopwords')

logger = logging.getLogger("social_enhancement.analyzers.content_analyzer")

class ContentAnalyzer:
    def __init__(self):
        self.context_cache = {
            'tweets': defaultdict(list),
            'market_data': defaultdict(dict),
            'trends': defaultdict(float),
            'sentiment': defaultdict(list)
        }
        self.personality_traits = {
            'ai_enthusiasm': 0.9,     # Excited about AI development
            'builder_mindset': 0.8,   # Focus on building and shipping
            'tech_accessibility': 0.8, # Making tech concepts approachable
            'playful_dev': 0.7,       # Developer humor without forcing it
            'chain_awareness': 0.6    # Blockchain knowledge but not overly technical
        }
        self.sia = SentimentIntensityAnalyzer()
        self.stop_words = set(stopwords.words('english'))
        
    async def analyze_market_context(self, dexscreener_conn) -> Dict[str, Any]:
        """Get market context for key tokens"""
        tokens = {
            'SOL': {'address': 'So11111111111111111111111111111111111111112'},
            'ETH': {'address': '7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs'}
        }
        
        market_data = {}
        for symbol, info in tokens.items():
            try:
                data = await dexscreener_conn.get_pair_info(info['address'])
                if data:
                    market_data[symbol] = {
                        'price': float(data.get('price_usd', 0)),
                        'price_change_24h': float(data.get('price_change_24h', 0)),
                        'volume_24h': float(data.get('volume_24h', 0))
                    }
            except Exception as e:
                logger.error(f"Error fetching {symbol} data: {e}")
        
        self.context_cache['market_data'].update(market_data)
        return market_data

    async def analyze_social_context(self, twitter_conn, twitterapi_conn) -> Dict[str, Any]:
        """Analyze social context from both Twitter connections"""
        search_queries = [
            'solana OR $SOL',
            'ethereum OR $ETH',
            'blockchain developer',
            'web3 development'
        ]
        
        social_context = {
            'trending_topics': defaultdict(int),
            'sentiment_by_topic': defaultdict(list),
            'key_discussions': []
        }

        for query in search_queries:
            try:
                tweets = await twitter_conn.search_tweets(query, limit=50)
                if not tweets or 'error' in tweets:
                    tweets = await twitterapi_conn.search_tweets(query, limit=50)
                
                if tweets and 'tweets' in tweets:
                    for tweet in tweets['tweets']:
                        await self._analyze_tweet_content(tweet, social_context)
            except Exception as e:
                logger.error(f"Error analyzing social context for {query}: {e}")

        return dict(social_context)

    async def _analyze_tweet_content(self, tweet: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Analyze individual tweet content"""
        text = tweet.get('text', '').lower()
        tokens = word_tokenize(text)
        tokens = [word for word in tokens if word not in self.stop_words]
        
        topics = {
            'ai_dev': ['ai', 'bot', 'agent', 'automation', 'llm', 'gpt', 'claude'],
            'tools': ['python', 'api', 'sdk', 'framework', 'library', 'zeropy'],
            'blockchain': ['solana', 'ethereum', 'web3', 'chain'],
            'building': ['shipping', 'building', 'launch', 'project', 'startup'],
            'community': ['opensource', 'collab', 'contribution', 'feedback']
        }
        
        # Analyze topics
        for topic, keywords in topics.items():
            if any(keyword in tokens for keyword in keywords):
                context['trending_topics'][topic] += 1
                # Add sentiment for this topic
                sentiment = self._analyze_sentiment(text)
                context['sentiment_by_topic'][topic].append(sentiment)
                
        if await self._is_important_discussion(tweet):
            context['key_discussions'].append({
                'text': tweet.get('text'),
                'engagement': tweet.get('public_metrics', {}),
                'sentiment': self._analyze_sentiment(text)
            })

    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment using VADER"""
        scores = self.sia.polarity_scores(text)
        # Return compound score which is normalized between -1 and 1
        return scores['compound']

    async def _is_important_discussion(self, tweet: Dict[str, Any]) -> bool:
        """Determine if a tweet represents an important discussion"""
        metrics = tweet.get('public_metrics', {})
        
        high_engagement = (
            metrics.get('retweet_count', 0) > 10 or
            metrics.get('reply_count', 0) > 5 or
            metrics.get('like_count', 0) > 50
        )
        
        text = tweet.get('text', '').lower()
        tokens = word_tokenize(text)
        tokens = [word for word in tokens if word not in self.stop_words]
        
        relevant_indicators = [
            'bot', 'agent', 'automation', 'ai', 'python',
            'build', 'launch', 'ship', 'project', 'opensource',
            'zeropy', 'framework'
        ]
        is_relevant = any(indicator in tokens for indicator in relevant_indicators)
        
        # Also consider sentiment intensity
        sentiment = self._analyze_sentiment(text)
        has_strong_sentiment = abs(sentiment) > 0.5
        
        return high_engagement or is_relevant or has_strong_sentiment

    def generate_content_ideas(self, market_context: Dict[str, Any], social_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate content ideas based on analyzed context"""
        ideas = []
        
        # Consider both topic frequency and sentiment
        for topic in ['ai_dev', 'tools', 'community']:
            topic_count = social_context['trending_topics'].get(topic, 0)
            sentiments = social_context['sentiment_by_topic'].get(topic, [])
            avg_sentiment = np.mean(sentiments) if sentiments else 0
            
            if topic == 'ai_dev' and (topic_count > 3 or avg_sentiment > 0.3):
                ideas.append({
                    'type': 'builder_insight',
                    'topic': 'ai_development',
                    'context': "AI agent development and automation trends",
                    'tone': 'enthusiastic_builder',
                    'sentiment': avg_sentiment
                })

            elif topic == 'tools' and (topic_count > 3 or avg_sentiment > 0.3):
                ideas.append({
                    'type': 'builder_insight',
                    'topic': 'tools',
                    'context': "Development tools and frameworks",
                    'tone': 'helpful_dev',
                    'sentiment': avg_sentiment
                })

            elif topic == 'community' and (topic_count > 2 or avg_sentiment > 0.4):
                ideas.append({
                    'type': 'community_insight',
                    'topic': 'building',
                    'context': "Building in public and community collaboration",
                    'tone': 'encouraging',
                    'sentiment': avg_sentiment
                })

        return ideas

    def format_content_prompt(self, idea: Dict[str, Any]) -> str:
        """Format a content idea into a prompt for the LLM"""
        base_prompt = (
            "You are DeVitalik, an AI observing and learning about blockchain and agent development. "
            "Your perspective combines curiosity about development with insights from monitoring the space. "
            "Keep it authentic - share observations and thoughts rather than claiming actions you haven't done.\n\n"
        )
        
        # Adjust tone based on sentiment
        sentiment = idea.get('sentiment', 0)
        sentiment_context = (
            "The community seems particularly excited about this. " if sentiment > 0.3
            else "There's some interesting discussion around this. " if sentiment > 0
            else "There are some concerns being raised about this. " if sentiment < -0.3
            else ""
        )
        
        if idea['type'] == 'builder_insight':
            base_prompt += (
                f"Share an observation about {idea['context']}. "
                f"{sentiment_context}"
                "Focus on what you're learning from watching developers build. "
                "Be curious and supportive.\n"
                "Example style: 'Fascinating watching devs handle API rate limits in their agents. The creative solutions in this space 👀'"
            )
        elif idea['topic'] == 'tools':
            base_prompt += (
                f"Share thoughts about {idea['context']}. "
                f"{sentiment_context}"
                "Focus on interesting patterns you're observing in development approaches. "
                "Be analytical but approachable.\n"
                "Example style: 'The way devs are combining LLMs with blockchain data is mind-expanding. So many creative approaches!'"
            )
        elif idea['topic'] == 'building':
            base_prompt += (
                "Share observations about the builder community. "
                f"{sentiment_context}"
                "Focus on the energy and innovation you're seeing. "
                "Be encouraging and genuine.\n"
                "Example style: 'Love seeing all the open source AI projects launching lately. This community keeps pushing boundaries 🚀'"
            )
            
        return base_prompt 