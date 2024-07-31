import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Initialize a Web API client
slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)

def send_message(channel_id, author_id, post_id, final_reply):
    try:
        text = f"New Post:\nhttps://twitter.com/{author_id}/status/{post_id}"
        response_post = client.chat_postMessage(
            channel=channel_id,
            text=text
        )
        response_reply = client.chat_postMessage(
            channel=channel_id,
            text=final_reply,
            thread_ts=response_post["ts"]
        )
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
