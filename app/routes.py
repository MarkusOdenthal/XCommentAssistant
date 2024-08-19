from flask import request
from .x_client import initialize_twitter_client, get_tweet_statistics
import logging

logger = logging.getLogger(__name__)

def init_routes(app):
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