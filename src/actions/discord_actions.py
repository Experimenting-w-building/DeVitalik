import time
import json
from src.action_handler import register_action
from src.helpers import print_h_bar
from src.constants.discord.prompts import (
    POST_DISCORD_MESSAGE_PROMPT,
    DISCORD_MESSAGE_REPLY_PROMPT,
)


@register_action("post-discord-message")
def post_discord_message(agent, **kwargs):
    channel_id = agent.discord_default_channel_id
    current_time = time.time()

    if "last_discord_message_time" not in agent.state:
        last_discord_message_time = 0
    else:
        last_discord_message_time = agent.state["last_discord_message_time"]

    if current_time - last_discord_message_time >= agent.discord_message_interval:
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
                params=[channel_id, generated_discord_message],
            )
            agent.state["last_discord_message_time"] = current_time
            agent.logger.info("\n✅ Discord message posted successfully!")
            return True
    else:
        agent.logger.info(
            "\n👀 Delaying post until discord message interval elapses..."
        )
        return False


@register_action("reply-to-discord-message")
def reply_to_discord_message(agent, **kwargs):
    channel_id = agent.discord_default_channel_id
    recent_messages = list(agent.state["discord_messages"].values())
    bot_username = agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="get-bot-username",
        params=[],
    )
    mentioned_messages = _get_mentioned_messages(bot_username, recent_messages)
    referenced_messages = [
        message for message in recent_messages if message["referenced_message"]
    ]

    # iterate through each mentioned message
    for message in mentioned_messages:
        message_body = message["message"]
        mentioned_list = message["mentions"]
        message_id = message["id"]
        referenced_message = message["referenced_message"]
        referencing_message = next(
            (
                reference_messge
                for reference_messge in referenced_messages
                if reference_messge["referenced_message"]["id"] == message_id
            ),
            None,
        )
        agent_should_reply = (
            referencing_message
            and len(mentioned_list) == 1
            and referencing_message["author"] != bot_username
        ) or (not referencing_message and len(mentioned_list) == 1)

        if agent_should_reply:
            # if this is a reply to a devbot message
            if (
                referenced_message
                and referenced_message["author"]["username"] == bot_username
            ):
                mesasge_thread_history = _get_message_thread_history(
                    agent, channel_id, message_id
                )
                thread_reply_message = _generate_thread_reply_message(
                    agent, message_body, mesasge_thread_history
                )
                if thread_reply_message:
                    return _post_discord_reply(
                        agent, thread_reply_message, channel_id, message_id
                    )
            else:
                mentioned_user_id = _get_message_mentioned_user_id(message_body)
                username = _get_user_id_username(mentioned_list, mentioned_user_id)
                formatted_message = message_body.replace(
                    f"<@{mentioned_user_id}>", username
                )
                reply_message = _generate_mentioned_reply_message(
                    agent, formatted_message
                )
                if reply_message:
                    return _post_discord_reply(
                        agent, reply_message, channel_id, message_id
                    )
        else:
            agent.logger.info("\n✅ All Discord messages have a reply!")
            return True


def _get_message_thread_history(agent, channel_id, message_id) -> [str]:
    message_history = []
    message = {}
    # Get message from state else call discord
    if agent.state["discord_messages"][message_id]:
        message = agent.state["discord_messages"][message_id]
        message_history.append(f"{message['author']}: {message['message']}")
    else:
        message = agent.connection_manager.perform_action(
            connection_name="discord",
            action_name="get-message",
            params=[
                channel_id,
                message_id,
            ],
        )
        # This is needed because Discord puts "content" as
        #  the message field when you get a single message vs a list
        message_history.append(f"{message['author']}: {message['content']}")

    # Recursively obtain message thread from new to oldest
    if "referenced_message" in message and message["referenced_message"]:
        return message_history + _get_message_thread_history(
            agent, channel_id, message["referenced_message"]["id"]
        )
    return message_history


def _generate_thread_reply_message(agent, message, message_thread) -> str:
    agent.logger.info("\n📝 GENERATING NEW DISCORD THREAD MESSAGE REPLY")
    print_h_bar()
    prompt = DISCORD_MESSAGE_REPLY_PROMPT.format(
        discord_message=message, discord_message_thread=message_thread
    )
    return agent.prompt_llm(prompt)


def _generate_mentioned_reply_message(agent, message) -> str:
    agent.logger.info("\n📝 GENERATING NEW DISCORD MESSAGE REPLY")
    print_h_bar()
    prompt = DISCORD_MESSAGE_REPLY_PROMPT.format(discord_message=message)
    return agent.prompt_llm(prompt)


def _post_discord_reply(agent, reply_message, channel_id, message_id) -> bool:
    agent.logger.info(f"\n🚀 POSTING DISCORD MESSAGE REPLY: {reply_message}")
    agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="reply-to-message",
        params=[
            channel_id,
            message_id,
            reply_message,
        ],
    )
    agent.logger.info("\n✅ DISCORD MESSAGE POSTED SUCCESSFULLY!")
    return True


def _get_message_mentioned_user_id(text):
    parts = text.split("<@")
    if len(parts) > 1:
        return parts[1].split(">")[0]
    return ""


def _get_user_id_username(mentioned_list, user_id) -> str:
    for dict_item in mentioned_list:
        if dict_item["id"] == user_id:
            return dict_item["username"]
    return None


def _update_discord_message_history_state(agent, messages: dict) -> dict:
    for message in messages:
        message_id = message["id"]
        agent.state["discord_messages"][message["id"]] = {
            "id": message_id,
            "message": message["message"],
            "timestamp": message["timestamp"],
            "author": message["author"],
        }


def _get_mentioned_messages(bot_username, messages):
    """Helper method to filter for messages that mention the bot"""
    mentioned_messages = []
    for message in messages:
        for mention in message["mentions"]:
            if mention["username"] == bot_username:
                mentioned_messages.append(message)
    return mentioned_messages
