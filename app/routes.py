from flask import request
from .x_client import initialize_twitter_client, get_tweet_statistics
import logging
from langsmith import Client

logger = logging.getLogger(__name__)

def init_routes(app):
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
            logger.info("Example added successfully")
            return {"message": "Example added successfully"}, 200

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}", exc_info=True)
            return {"error": str(e)}, 500
        
    @app.route("/tweet_statistics", methods=["POST"])
    def tweet_statistics():
        try:
            data = request.get_json()
            tweet_url = data.get("tweet_url")

            if not tweet_url:
                return {"error": "No tweet URL provided"}, 400
            
            client = initialize_twitter_client()
            stats = get_tweet_statistics(client, tweet_url)
            return stats

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}", exc_info=True)
            return {"error": str(e)}, 500