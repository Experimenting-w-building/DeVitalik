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
        tweet = agent.state["timeline_tweets"].pop(0)
        tweet_id = tweet.get('id')
        if not tweet_id:
            return

        agent.logger.info(f"\n💬 GENERATING REPLY to: {tweet.get('text', '')[:50]}...")

        for attempt in range(MAX_RETRIES):
            base_prompt = REPLY_TWEET_PROMPT.format(tweet_text=tweet.get('text'))
            if attempt > 0:
                # Add stronger length constraint on retry
                base_prompt = f"Generate a VERY CONCISE reply (must be under {MAX_TWEET_LENGTH} characters). {base_prompt}"
            
            system_prompt = agent._construct_system_prompt()
            reply_text = agent.prompt_llm(prompt=base_prompt, system_prompt=system_prompt)

            if reply_text and len(reply_text) <= MAX_TWEET_LENGTH:
                agent.logger.info(f"\n🚀 Posting reply: '{reply_text}'")
                agent.connection_manager.perform_action(
                    connection_name="twitter",
                    action_name="reply-to-tweet",
                    params=[tweet_id, reply_text]
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
