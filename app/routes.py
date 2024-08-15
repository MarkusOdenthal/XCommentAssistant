from flask import request, current_app
from .x_client import initialize_twitter_client, get_tweet_statistics
from .topic_classification import topic_classification
import logging

logger = logging.getLogger(__name__)

def init_routes(app):
    @app.route("/add_label_data_to_topic_classification", methods=["POST"])
    def add_label_data_to_topic_classification():
        try:
            ls_client = current_app.config['ls_client']
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

    @app.route("/interesting_topic_classification", methods=["POST"])
    def interesting_topic_classifier():
        try:
            data = request.get_json()
            tweet = data.get("tweet")

            if not tweet:
                logger.warning("No tweet provided in the request")
                return {"error": "No tweet provided"}, 400

            classification = topic_classification(tweet)
            return {"classification": classification}

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