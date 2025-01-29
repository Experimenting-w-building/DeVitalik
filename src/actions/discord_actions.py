import time
import json
from src.action_handler import register_action
from src.helpers import print_h_bar
from src.constants.discord.prompts import (
    POST_DISCORD_MESSAGE_PROMPT,
    DISCORD_MESSAGE_REPLY_PROMPT,
    DISCORD_MESSAGE_THREAD_REPLY_PROMPT,
    DISCORD_MESSAGE_THREAD_REPLY_PROMPT_UNDER1000,
    DISCORD_MESSAGE_REPLY_PROMPT_UNDER1000,
    PINECONE_RESULTS_ZEREPY_PROMPT,
    INTENT_FROM_MESSAGE
)
from langchain.text_splitter import CharacterTextSplitter


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
    max_discord_reply_length = 2000
    channel_id = agent.discord_default_channel_id
    recent_messages = list(agent.state["discord_messages"].values())
    bot_metadata = agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="get-bot-metadata",
        params=[],
    )
    bot_username = bot_metadata['username']
    bot_id = bot_metadata['id']
    mentioned_messages = _get_mentioned_messages(bot_id, recent_messages)
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
            and referencing_message["author_id"] != bot_id
            and message["author_id"] != bot_id
        ) or (
            not referencing_message
            and len(mentioned_list) == 1
            and message["author_id"] != bot_id
        )

        if agent_should_reply:
            pinecone_results = _get_pinecone_results(agent, message_body)

            model = _get_intent_with_model(agent, message_body)

            if (
                referenced_message
                and referenced_message["author"]["id"] == bot_id
            ):
                mesasge_thread_history = _get_message_thread_history(
                    agent, channel_id, message_id
                )
                thread_reply_message = _generate_thread_reply_message(
                    agent,
                    message_body,
                    mesasge_thread_history,
                    pinecone_results,
                    bot_username,
                    model=model
                )
                if thread_reply_message:
                    if len(thread_reply_message) > max_discord_reply_length:
                        _post_long_discord_message(
                            agent, channel_id, message_id, thread_reply_message
                        )
                    else:
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
                    agent, formatted_message, pinecone_results, model
                )
                if reply_message:
                    if len(reply_message) > max_discord_reply_length:
                        _post_long_discord_message(
                            agent, channel_id, message_id, reply_message
                        )
                    else:
                        return _post_discord_reply(
                            agent, reply_message, channel_id, message_id
                        )
    agent.logger.info("\n✅ All Discord messages have a reply!")
    return True


# Method to break down long replies and post chunked messages to discord
def _post_long_discord_message(agent, channel_id, message_id, reply_message):
    latest_thread_message_id = message_id
    chunks = _split_markdown_by_size(reply_message)
    for chunk in chunks:
        if len(chunk) > 2000:
            chunk_split = split_by_size(chunk, 2000)
            for split in chunk_split:
                response = _post_discord_reply(
                    agent, chunk, channel_id, latest_thread_message_id
                )
                # capture message id so that the next chunk is a reply to itself, continuing the thread
                latest_thread_message_id = response["id"]
        else:
            response = _post_discord_reply(
                agent, chunk, channel_id, latest_thread_message_id
            )
            # capture message id so that the next chunk is a reply to itself, continuing the thread
            latest_thread_message_id = response["id"]

def split_by_size(string, size):
    return [string[i:i + size] for i in range(0, len(string), size)]

# Method to break down a markdown file by character size
def _split_markdown_by_size(markdown_text, chunk_size=2000, chunk_overlap=0):
    text_splitter = CharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_text(markdown_text)
    return chunks


def _get_message_thread_history(agent, channel_id, message_id) -> [str]:
    message_history = []
    message = {}
    # Get message from state else call discord
    if agent.state["discord_messages"][message_id]:
        message = agent.state["discord_messages"][message_id]
        message_history.append(f"{message['author_id']}: {message['message']}")
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
        message_history.append(f"{message['author_id']}: {message['content']}")

    # Recursively obtain message thread from new to oldest
    if "referenced_message" in message and message["referenced_message"]:
        return message_history + _get_message_thread_history(
            agent, channel_id, message["referenced_message"]["id"]
        )
    return message_history


def _generate_thread_reply_message(
    agent, message, message_thread, pinecone_results, bot_username, model
) -> str:
    agent.logger.info("\n📝 GENERATING NEW DISCORD THREAD MESSAGE REPLY")
    print_h_bar()
    if model == "o1-mini":
        prompt = DISCORD_MESSAGE_THREAD_REPLY_PROMPT.format(
            discord_message=message,
            discord_message_thread=message_thread,
            bot_username=bot_username,
        )
    else:
        prompt = DISCORD_MESSAGE_THREAD_REPLY_PROMPT_UNDER1000.format(
            discord_message=message,
            discord_message_thread=message_thread,
            bot_username=bot_username,
        )
    return agent.prompt_llm(prompt, system_prompt=pinecone_results, model=model)


def _generate_mentioned_reply_message(agent, message, pinecone_results, model) -> str:
    agent.logger.info("\n📝 GENERATING NEW DISCORD MESSAGE REPLY")
    print_h_bar()
    if model == "o1-mini":
        prompt = DISCORD_MESSAGE_REPLY_PROMPT.format(discord_message=message)
    else:
        prompt = DISCORD_MESSAGE_REPLY_PROMPT_UNDER1000.format(discord_message=message)  
    return agent.prompt_llm(prompt, system_prompt=pinecone_results, model=model)


def _post_discord_reply(agent, reply_message, channel_id, message_id) -> dict:
    agent.logger.info(f"\n🚀 POSTING DISCORD MESSAGE REPLY: {reply_message}")
    response = agent.connection_manager.perform_action(
        connection_name="discord",
        action_name="reply-to-message",
        params=[
            channel_id,
            message_id,
            reply_message,
        ],
    )
    agent.logger.info("\n✅ DISCORD MESSAGE POSTED SUCCESSFULLY!")
    return response


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


def _get_mentioned_messages(bot_id, messages) -> dict:
    """Helper method to filter for messages that mention the bot"""
    mentioned_messages = []
    for message in messages:
        for mention in message["mentions"]:
            if mention["id"] == bot_id:
                mentioned_messages.append(message)
    return mentioned_messages


def _get_pinecone_results(agent, message):
    message_embedding = agent.generate_embeddings([message])
    pinecone_results = agent.query_embeddings("blorm-network-zerepy", message_embedding)
    return PINECONE_RESULTS_ZEREPY_PROMPT.format(pinecone_results=pinecone_results)


def _get_intent_with_model(agent, message):
    system_prompt = INTENT_FROM_MESSAGE.format(message=message)
    res = agent.prompt_llm(message, system_prompt, "gpt-4o-mini")
    print(res)
    return res