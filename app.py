import logging
import os
from datetime import datetime

import cohere
import requests
import tweepy
from flask_apscheduler import APScheduler
from flask import Flask, request
from langchain import hub
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser, XMLOutputParser
from langchain_openai import ChatOpenAI
from langsmith import Client, traceable
from langsmith.run_helpers import get_current_run_tree

from config import (
    AUDIENCE,
    COPYWRITING_STYLE,
    PERSONAL_INFORMATION,
)
from semantic_search.upsert_pinecone import query_index
from x.x import get_user_info, initialize_twitter_client

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True

app = Flask(__name__)
app.config.from_object(Config())

# initialize scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# test scheduler
@scheduler.task('interval', id='do_job', seconds=3, misfire_grace_time=900)
def job():
    print("Scheduled job executed")
    print(f"Time: {datetime.now()}")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

co = cohere.Client(os.getenv("COHERE_API_KEY"))

ls_client = Client()
# label_data = ls_client.list_examples(dataset_name="XCommentClassification")
# examples = []
# for entry in label_data:
#     post = entry.inputs["text"]
#     label = entry.outputs["label"]
#     examples.append(ClassifyExample(text=post, label=label))

prompt = hub.pull("x_comment_prompt")
model = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.5,
)
parser = XMLOutputParser()
chain = prompt | model | parser

gpt_4o_mini = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)
viral_social_media_comments_ideas_prompt = hub.pull("viral_social_media_comments_ideas")

str_parser = StrOutputParser()
viral_social_media_comments_ideas_chain = (
    viral_social_media_comments_ideas_prompt | gpt_4o_mini | str_parser
)

sonnet_3_5_0 = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.0,
)
viral_social_media_comments_refine_prompt = hub.pull(
    "viral_social_media_comments_refine"
)
viral_social_media_comments_refine_chain = (
    viral_social_media_comments_refine_prompt | sonnet_3_5_0 | parser
)


@traceable(
    run_type="chain",
    name="topic_classification",
)
def topic_classification(post: str):
    # app.logger.info(f"Number of Examples: {len(examples)}")
    # response = co.classify(model="embed-english-v3.0", inputs=[post], examples=examples)
    response = co.classify(
        model="dd74f49b-dfcb-45fc-ac5f-bafa23eff44b-ft", inputs=[post]
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


@app.route("/add_label_data_to_topic_classification", methods=["POST"])
def add_label_data_to_topic_classification():
    ls_client = Client()
    try:
        data = request.get_json()
        post = data.get("post")
        label = data.get("label")

        if not post or not label:
            return {"error": "Post and label are required"}, 400

        _ = ls_client.create_examples(
            inputs=[{"text": post}],
            outputs=[{"label": label}],
            dataset_name="XCommentClassification",
        )
        try:
            # response = requests.post(os.getenv("RENDER_DEPLOYMENT_HOOK_URL"))
            # response.raise_for_status()
            logger.info("Deployment paused for now")
            return {
                "message": "Example added successfully and deployment triggered",
                "deployment_status": "initiated",
            }, 200
        except requests.RequestException as e:
            # Log the error for internal tracking
            app.logger.error(f"Deployment hook failed: {str(e)}")

            return {
                "message": "Example added successfully, but deployment trigger failed",
                "deployment_status": "failed",
                "error": str(e),
            }, 207  # Returning 207 Multi-Status to indicate partial success

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500


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


@app.route("/generate_comment_viral", methods=["POST"])
def generate_comment_viral():
    try:
        data = request.get_json()
        tweet = data.get("tweet")
        author_id = int(data.get("author_id"))
        client = initialize_twitter_client()
        user_info = get_user_info(client, user_id=author_id)
        if user_info:
            user_name = user_info.get("name", "")
            user_description = user_info.get("description", "")
        else:
            user_name = ""
            user_description = ""

        if not tweet:
            logger.warning("No tweet provided in the request")
            return {"error": "No tweet provided"}, 400

        example_comments = query_index("x-comments-markus-odenthal", tweet).matches
        example_comments = [
            comment
            for comment in example_comments
            if int(comment["metadata"]["original_post_author_id"]) != 753027473193873408
        ]

        example_comments_str = ""
        for idx, comment in enumerate(example_comments):
            example_comments_str += f"Post: {1 + idx}\n"
            example_comments_str += comment.metadata["original_post"] + "\n"
            example_comments_str += "-" * 50 + "\n"
            example_comments_str += f"Reply: {1 + idx}\n"
            example_comments_str += comment.metadata["reply"] + "\n"
            example_comments_str += "=" * 50 + "\n"

        example_posts = query_index("x-posts-markus-odenthal", tweet).matches
        example_posts_str = ""
        for idx, post in enumerate(example_posts):
            example_posts_str += f"Post: {1 + idx}\n"
            example_posts_str += post.metadata["text"] + "\n"
            example_posts_str += "-" * 50 + "\n"

        ideas = viral_social_media_comments_ideas_chain.invoke(
            {
                "AUDIENCE_INFO": AUDIENCE,
                "PERSONAL_INFORMATION": PERSONAL_INFORMATION,
                "PREVIOUS_POSTS": example_posts_str,
                "EXAMPLE_COMMENTS": example_comments_str,
                "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
                "POST_TO_COMMENT_ON": tweet,
            }
        )

        final_comment = viral_social_media_comments_refine_chain.invoke(
            {
                "AUDIENCE_INFO": AUDIENCE,
                "PERSONAL_INFORMATION": PERSONAL_INFORMATION,
                "EXAMPLE_COMMENTS": example_comments_str,
                "PREVIOUS_POSTS": example_posts_str,
                "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
                "POST_TO_REPLY": tweet,
                "COPYWRITING_STYLE": COPYWRITING_STYLE,
                "REPLY_IDEAS": ideas,
            }
        )
        final_reply = final_comment["root"][1]["final_reply"]
        return {"final_reply": final_reply}

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
            consumer_secret=os.getenv("X_ACCESS_CONSUMER_SECRET"),
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
