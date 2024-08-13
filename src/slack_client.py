import os

import modal

image = modal.Image.debian_slim(python_version="3.11").pip_install("slack-sdk")
with image.imports():
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

app = modal.App(
    "slack", image=image, secrets=[modal.Secret.from_name("SocialMediaManager")]
)


@app.function()
def send_message(
    channel_id: str,
    author_id: str,
    post_id: str,
    final_reply: str,
    example_comment: dict,
):
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)
    try:
        block = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Hey Future *Reply Guy* I found a new intersting Post",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Here is some inspiration from a past reply.\n*Similarity Score: {round(example_comment['score'], 2)}*",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Post:*\n{example_comment['metadata']['original_post']}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*My Reply:*\n{example_comment['metadata']['reply']}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*New Post:* \nhttps://twitter.com/{author_id}/status/{post_id}",
                },
            },
        ]

        response_post = client.chat_postMessage(
            channel=channel_id, text="New Post", blocks=block
        )
        response_reply = client.chat_postMessage(
            channel=channel_id, text=final_reply, thread_ts=response_post["ts"]
        )
        return None
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
