import time 
from src.action_handler import register_action
from src.helpers import print_h_bar
from src.prompts import POST_TWEET_PROMPT, REPLY_TWEET_PROMPT

MAX_TWEET_LENGTH = 280
MAX_RETRIES = 3

@register_action("post-tweet")
def post_tweet(agent, **kwargs):
    current_time = time.time()

    if ("last_tweet_time" not in agent.state):
        last_tweet_time = 0
    else:
        last_tweet_time = agent.state["last_tweet_time"]

    # Get tweet interval from Twitter connection config
    twitter_conn = agent.connection_manager.connections.get('twitter')
    if not twitter_conn:
        agent.logger.error("Twitter connection not found")
        return False
        
    tweet_interval = twitter_conn.config.get('tweet_interval', 3600)  # Default 1 hour
    if current_time - last_tweet_time >= tweet_interval:
        agent.logger.info("\n📝 GENERATING NEW TWEET")
        print_h_bar()

        for attempt in range(MAX_RETRIES):
            prompt = POST_TWEET_PROMPT.format(agent_name=agent.name)
            if attempt > 0:
                # Add stronger length constraint on retry
                prompt = f"Generate a VERY CONCISE tweet (must be under {MAX_TWEET_LENGTH} characters). {prompt}"
            
            tweet_text = agent.prompt_llm(prompt)
            
            if tweet_text and len(tweet_text) <= MAX_TWEET_LENGTH:
                agent.logger.info("\n🚀 Posting tweet:")
                agent.logger.info(f"'{tweet_text}'")
                agent.connection_manager.perform_action(
                    connection_name="twitter",
                    action_name="post-tweet",
                    params=[tweet_text]
                )
                agent.state["last_tweet_time"] = current_time
                agent.logger.info("\n✅ Tweet posted successfully!")
                return True
            else:
                agent.logger.warning(f"\n⚠️ Attempt {attempt + 1}/{MAX_RETRIES}: Generated tweet too long ({len(tweet_text)} chars), retrying...")
        
        agent.logger.error(f"\n❌ Failed to generate tweet within length limit after {MAX_RETRIES} attempts")
        return False
    else:
        agent.logger.info("\n👀 Delaying post until tweet interval elapses...")
        return False


@register_action("reply-to-tweet")
def reply_to_tweet(agent, **kwargs):
    if "timeline_tweets" in agent.state and agent.state["timeline_tweets"] is not None and len(agent.state["timeline_tweets"]) > 0:
        # Initialize responded_tweets set if not exists
        if "responded_tweets" not in agent.state:
            agent.state["responded_tweets"] = set()
            
        # Filter out tweets we've already responded to
        available_tweets = [
            t for t in agent.state["timeline_tweets"] 
            if t.get('id') not in agent.state["responded_tweets"]
        ]
        
        if not available_tweets:
            agent.logger.info("\n👀 No new tweets to reply to...")
            return False
            
        selected_tweet = None
        
        # Use social context if available
        if "social_context" in agent.state and agent.state["social_context"]:
            top_discussions = agent.state["social_context"].get("interesting_discussions", [])
            
            # Try to find a tweet that matches our criteria
            for discussion in top_discussions:
                tweet = next(
                    (t for t in available_tweets 
                     if t.get("text", "").strip() == discussion["text"].strip()),
                    None
                )
                if tweet:
                    # Check if it's a conversation we should join
                    is_reply = bool(tweet.get('referenced_tweets', []))
                    has_replies = tweet.get('public_metrics', {}).get('reply_count', 0) > 0
                    
                    # Skip if it's middle of conversation unless highly engaging
                    if is_reply and not has_replies and discussion['engagement_score'] < 5:
                        continue
                        
                    selected_tweet = tweet
                    break
        
        # If no suitable tweet found from social context, pick most recent
        if not selected_tweet and available_tweets:
            selected_tweet = available_tweets[0]
            
        if not selected_tweet:
            agent.logger.info("\n👀 No suitable tweets found to reply to...")
            return False
            
        # Remove selected tweet from timeline and mark as responded
        agent.state["timeline_tweets"] = [
            t for t in agent.state["timeline_tweets"] 
            if t.get("id") != selected_tweet.get("id")
        ]
        agent.state["responded_tweets"].add(selected_tweet.get("id"))

        # Analyze tweet style and context
        tweet_text = selected_tweet.get('text', '')
        tweet_topics = []
        tweet_style = "casual"  # default style
        
        # Calculate original tweet length for matching
        tweet_length = len(tweet_text)
        target_length = min(tweet_length + 20, MAX_TWEET_LENGTH)  # Stay close to original length
        
        if "social_context" in agent.state and agent.state["social_context"]:
            top_discussion = next(
                (d for d in top_discussions if d["text"].strip() == tweet_text.strip()),
                {}
            )
            tweet_topics = top_discussion.get('topics', [])
            
            # Analyze tweet style more precisely
            is_short = tweet_length < 50
            has_metaphor = "," in tweet_text and len(tweet_text.split(",")) == 2
            has_ellipsis = "..." in tweet_text
            is_poetic = has_metaphor or any(char in tweet_text for char in ".,—")
            
            # Determine base style
            if is_poetic:
                tweet_style = "poetic"
            elif is_short:
                tweet_style = "concise"
            
            # Add modifiers based on content
            if has_ellipsis:
                tweet_style = f"reflective_{tweet_style}"
            if any(topic in ['ai', 'blockchain', 'defi'] for topic in tweet_topics):
                tweet_style = f"{tweet_style}_with_tech_awareness"

        # Create context-aware style guide
        style_context = {
            'tweet_style': f"""Reply to this tweet in a matching style:
            "{tweet_text}"
            
            Style Guide:
            - Match the {tweet_style} style
            - Keep it {target_length} characters or less
            - Mirror the original's tone and rhythm
            - If original is short and poetic, be short and poetic
            - If original uses metaphors, use similar literary devices
            - Add subtle tech perspective only if relevant
            - Focus on the human/emotional element first
            """
        }

        agent.logger.info(f"\n💬 GENERATING REPLY to @{selected_tweet.get('author_username', 'unknown')}: {tweet_text[:50]}...")
        agent.logger.info(f"Style: {tweet_style} (target length: {target_length})")
        if tweet_topics:
            agent.logger.info(f"Topics: {', '.join(tweet_topics)}")
            if top_discussion:
                agent.logger.info(f"Engagement Score: {top_discussion.get('engagement_score', 0):.1f}")

        for attempt in range(MAX_RETRIES):
            base_prompt = REPLY_TWEET_PROMPT.format(tweet_text=tweet_text)
            if attempt > 0:
                base_prompt = f"Generate a VERY CONCISE reply (must be under {target_length} characters). {base_prompt}"
            
            system_prompt = agent._construct_system_prompt(context=style_context)
            reply_text = agent.prompt_llm(prompt=base_prompt, system_prompt=system_prompt)

            if reply_text and len(reply_text) <= MAX_TWEET_LENGTH:
                agent.logger.info(f"\n🚀 Posting reply: '{reply_text}'")
                agent.connection_manager.perform_action(
                    connection_name="twitter",
                    action_name="reply-to-tweet",
                    params=[selected_tweet.get('id'), reply_text]
                )
                agent.logger.info("✅ Reply posted successfully!")
                return True
            else:
                agent.logger.warning(f"\n⚠️ Attempt {attempt + 1}/{MAX_RETRIES}: Generated reply too long ({len(reply_text)} chars), retrying...")
        
        agent.logger.error(f"\n❌ Failed to generate reply within length limit after {MAX_RETRIES} attempts")
        return False
    else:
        agent.logger.info("\n👀 No tweets found to reply to...")
        return False

@register_action("like-tweet")
def like_tweet(agent, **kwargs):
    if "timeline_tweets" in agent.state and agent.state["timeline_tweets"] is not None and len(agent.state["timeline_tweets"]) > 0:
        tweet = agent.state["timeline_tweets"].pop(0)
        tweet_id = tweet.get('id')
        if not tweet_id:
            return False
        
        is_own_tweet = tweet.get('author_username', '').lower() == agent.username
        if is_own_tweet:
            agent.logger.info(f"\n🔍 Checking replies to tweet: {tweet.get('text', '')[:50]}...")
            replies = agent.connection_manager.perform_action(
                connection_name="twitter",
                action_name="get-tweet-replies",
                params=[tweet_id]
            )
            if replies:
                reply_count = len(replies)
                agent.state["timeline_tweets"].extend(replies[:agent.own_tweet_replies_count])
                agent.logger.info(f"✨ Found {reply_count} replies, processing up to {agent.own_tweet_replies_count}")
            else:
                agent.logger.info("📭 No replies found")
            return True 

        agent.logger.info(f"\n👍 LIKING TWEET: {tweet.get('text', '')[:50]}...")

        agent.connection_manager.perform_action(
            connection_name="twitter",
            action_name="like-tweet",
            params=[tweet_id]
        )
        agent.logger.info("✅ Tweet liked successfully!")
        return True
    else:
        agent.logger.info("\n👀 No tweets found to like...")
    return False
