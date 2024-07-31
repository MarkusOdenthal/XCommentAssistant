import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize a Web API client
slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)

def send_message(channel_id, post, reply):
    try:
        response_post = client.chat_postMessage(
            channel=channel_id,
            text=post
        )
        response_reply = client.chat_postMessage(
            channel=channel_id,
            text=reply,
            thread_ts=response_post["ts"]
        )
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
