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
    channel_id = agent.default_channel_id
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
    channel_id = agent.default_channel_id
    bot_username = agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="get-bot-username",
        params=[],
    )

    # get mentioned messages
    mentioned_messages = agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="read-mentioned-messages",
        params=[channel_id, 10],
    )
    recent_messages = agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="read-messages",
        params=[channel_id, 10],
    )
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
                print(f"sending reply: {thread_reply_message}")
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
    message_context = agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="get-message",
        params=[
            channel_id,
            message_id,
        ],
    )
    message_history.append(message_context["content"])
    if "referenced_message" in message_context:
        return message_history + _get_message_thread_history(
            agent, channel_id, message_context["referenced_message"]["id"]
        )

    return message_history


def _generate_thread_reply_message(agent, message, message_thread) -> str:
    agent.logger.info("\n📝 GENERATING NEW DISCORD MESSAGE REPLY")
    print_h_bar()
    print(f"message to reply to: {message}")
    print(f"message thread: {message_thread}")
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
    agent.logger.info("\n🚀 Posting discord message reply:")
    agent.logger.info(f"'{reply_message}'")
    agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="reply-to-message",
        params=[
            channel_id,
            message_id,
            reply_message,
        ],
    )
    agent.logger.info("\n✅ Discord message posted successfully!")
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
