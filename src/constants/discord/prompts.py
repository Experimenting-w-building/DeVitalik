"""
This file contains the Discord prompt templates used for generating content in various tasks.
These templates are formatted strings that will be populated with dynamic data at runtime.
"""

POST_DISCORD_MESSAGE_PROMPT = (
    "Generate an engaging discord message. Don't include any hashtags, links or emojis. Keep it under 280 characters."
    "The discord message should be pure commentary, do not shill any coins or projects apart from {agent_name}. Do not repeat any of the"
    "discord messages that were given as example. Avoid the words AI and crypto."
)

DISCORD_MESSAGE_REPLY_PROMPT = 'Give me a direct answer, without anything else, for this discord message: "{discord_message}". Keep it under 2000 characters. Don\'t include any usernames, hashtags, links or emojis.'

DISCORD_MESSAGE_THREAD_REPLY_PROMPT = (
    'Given the context of this message thread (from new to old): {discord_message_thread} and this new message: "{discord_message}", give me a direct reply I can use.'
    "Your username is {bot_username} in the message thread."
    "You can use the additional date provided in the request if it makes sense to."
    "Keep it under 2000 characters. Don't include any usernames, hashtags, links or emojis."
)

PINECONE_RESULTS_ZEREPY_PROMPT = (
    "Generate a detailed explanation using the following search results about the Zerepy repository: {pinecone_results}"
    "The explanation should be clear, concise, and informative, providing insights into the repository's relevance and content."
)
