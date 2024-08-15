import logging
import os
from typing import Any, Dict, List, Optional

import modal
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

image = modal.Image.debian_slim(python_version="3.11").pip_install("slack-sdk")
with image.imports():
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

app = modal.App(
    "slack", image=image, secrets=[modal.Secret.from_name("SocialMediaManager")]
)


# Define the data model for the incoming payload
class RuntimeInfo(BaseModel):
    sdk: str
    sdk_version: str
    library: str
    platform: str
    runtime: str
    py_implementation: str
    runtime_version: str
    langchain_version: Optional[str]
    langchain_core_version: Optional[str]


class ExtraInfo(BaseModel):
    runtime: RuntimeInfo
    metadata: Dict[str, Any]


class RunData(BaseModel):
    modified_at: str
    extra: ExtraInfo
    session_id: str
    start_time: str
    end_time: str
    trace_id: str
    name: str
    outputs: Dict[str, str]
    inputs: Dict[str, str]
    status: str


class IncomingPayload(BaseModel):
    rule_id: str
    start_time: str
    end_time: str
    runs: List[RunData]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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


@app.function()
def send_classification_to_slack(post, label):
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    client = WebClient(token=slack_token)
    try:
        response = client.chat_postMessage(
            channel="C07BPF7TULQ",
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Label*: {label}"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Post*:\n{post}"},
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "interesting_topic"},
                            "value": post,
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "uninteresting_topic",
                            },
                            "value": post,
                            "style": "danger",
                        },
                    ],
                },
            ],
        )
        logger.info(f"Message sent: {response}")
    except SlackApiError as e:
        print(f"Error: {e}")


@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    send_classification_to_slack.local("This is a test post", "interesting")


@app.function()
@modal.web_endpoint(method="POST")
def classification_webhook(payload: IncomingPayload):
    # Assuming you care only about the first run (you could loop through if needed)
    run = payload.runs[0]

    # Extract the post and the label
    post = run.inputs.get("post", "")
    label = run.outputs.get("output", "")
    logger.info(f"Post: {post[:10]}, Label: {label}")

    # Call the function to send the data to Slack
    send_classification_to_slack.local(post=post, label=label)

    return HTMLResponse(f"<html>Notification sent for post: {post[:30]}...</html>")
