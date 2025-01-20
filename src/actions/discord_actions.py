import time
from src.action_handler import register_action
from src.helpers import print_h_bar
from src.constants.discord.prompts import POST_DISCORD_MESSAGE_PROMPT

"""
TODO: This file is abstract enough to share a commons impl between social platforms
        with argument on what social platform to post message(s) one.
"""

    # {"name": "post-discord-message", "weight": 1}


@register_action("post-discord-message")
def post_discord_message(agent, **kwargs):
    print("IN THE POST DISCORD MESSAGE")
    current_time = time.time()

    if "last_discord_message_time" not in agent.state:
        last_discord_message_time = 0
    else:
        last_discord_message_time = agent.state["last_discord_message_time"]

    if current_time - last_discord_message_time >= agent.discod_message_interval:
        agent.logger.info("\n📝 GENERATING NEW DISCORD MESSAGE")
        print_h_bar()

        prompt = POST_DISCORD_MESSAGE_PROMPT.format(agent_name=agent.name)
        generated_discord_message = agent.prompt_llm(prompt)

        if generated_discord_message:
            agent.logger.info("\n🚀 Posting discord message:")
            agent.logger.info(f"'{generated_discord_message}'")
            agent.connection_manager.perform_action(
                connection_name="discord",
                action_name="post-message",
                # todo: setup default channel id in config
                params=["1327792083599228971", generated_discord_message],
            )
            agent.state["last_discord_message_time"] = current_time
            agent.logger.info("\n✅ Discord message posted successfully!")
            return True
    else:
        agent.logger.info(
            "\n👀 Delaying post until discord message interval elapses..."
        )
        return False
