import logging
import os

import cohere
import tweepy
from cohere import ClassifyExample
from flask import Flask, request
from langchain import hub
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import XMLOutputParser
from langsmith import Client, traceable, trace
from langsmith.run_helpers import get_current_run_tree

from config import ANTI_VISION, BEHAVIORS, COMMENTS, SKILLS, VISION, YOUR_PAST

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

co = cohere.Client(os.getenv("COHERE_API_KEY"))

ls_client = Client()
label_data = ls_client.list_examples(dataset_name="XCommentClassification")
examples = []
for entry in label_data:
    post = entry.inputs["text"]
    label = entry.outputs["label"]
    examples.append(ClassifyExample(text=post, label=label))

prompt = hub.pull("x_comment_prompt")
model = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.2,
)
parser = XMLOutputParser()
chain = prompt | model | parser

@traceable(run_type="chain", name="topic_classification",)
def topic_classification(post: str):
    response = co.classify(
        model="embed-english-v3.0",
        inputs=[post],
        examples=examples
    )
    prediction = response.classifications[0].prediction
    confidence = response.classifications[0].confidence

    run = get_current_run_tree()
    run_id = run.id
    ls_client.create_feedback(
        run_id,
        key="confidence",
        score=confidence,
    )
    return prediction

@app.route("/interesting_topic_classification", methods=["POST"])
def interesting_topic_classifier():
    try:
        logger.info("Received request for topic classification")

        # Get the tweet from the incoming JSON request
        data = request.get_json()
        tweet = data.get("tweet")

        if not tweet:
            logger.warning("No tweet provided in the request")
            return {"error": "No tweet provided"}, 400

        logger.info(f"Classifying tweet: {tweet[:50]}...")

        # Classify the tweet
        classification = topic_classification(tweet)

        return {"classification": classification}

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500


@app.route("/generate_comment", methods=["POST"])
def generate_comment():
    try:
        data = request.get_json()
        tweet = data.get("tweet")

        if not tweet:
            logger.warning("No tweet provided in the request")
            return {"error": "No tweet provided"}, 400

        comments = chain.invoke(
            {
                "YOUR_PAST": YOUR_PAST,
                "SKILLS": SKILLS,
                "BEHAVIORS": BEHAVIORS,
                "ANTI_VISION": ANTI_VISION,
                "VISION": VISION,
                "COMMENTS": COMMENTS,
                "BIG_ACCOUNT_POST": tweet,
            }
        )

        return {"comments": comments["root"][1]}

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500


def get_tweet_statistics(tweet_url):
    try:
        # Extract tweet ID from URL
        tweet_id = tweet_url.split("/")[-1].split("?")[0]

        # Initialize Twitter API client
        client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
            consumer_key=os.getenv("X_ACCESS_CONSUMER_KEY"),
            consumer_secret=os.getenv("X_ACCESS_CONSUMER_SECRET")
        )
        # Fetch tweet data
        response = client.get_tweets(
            [tweet_id],
            tweet_fields=["public_metrics", "non_public_metrics"],
            user_auth=True,
        )

        if not response.data:
            return {"error": "Tweet not found or inaccessible"}

        metrics = {
            **response.data[0].public_metrics,
            **response.data[0].non_public_metrics,
        }
        return metrics

    except Exception as e:
        logger.error(f"Error fetching tweet statistics: {str(e)}", exc_info=True)
        return {"error": str(e)}


@app.route("/tweet_statistics", methods=["POST"])
def tweet_statistics():
    try:
        data = request.get_json()
        tweet_url = data.get("tweet_url")

        if not tweet_url:
            return {"error": "No tweet URL provided"}, 400

        stats = get_tweet_statistics(tweet_url)
        return stats

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(debug=True)
