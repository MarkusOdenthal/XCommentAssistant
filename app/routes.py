from flask import request, jsonify, current_app
from .pinecone_client import query_index
from .x_client import get_user_info, initialize_twitter_client, get_tweet_statistics
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

    @app.route("/generate_comment_viral", methods=["POST"])
    def generate_comment_viral():
        try:
            data = request.get_json()
            tweet = data.get("tweet")
            author_id = int(data.get("author_id"))
            client = initialize_twitter_client()
            user_info = get_user_info(client, user_id=author_id)
            user_name = user_info.get("name", "") if user_info else ""
            user_description = user_info.get("description", "") if user_info else ""

            if not tweet:
                logger.warning("No tweet provided in the request")
                return {"error": "No tweet provided"}, 400

            example_comments = query_index("x-comments-markus-odenthal", tweet).matches
            example_comments_str = "\n".join([
                f"Post: {idx + 1}\n{comment.metadata['original_post']}\n{'-'*50}\nReply: {idx + 1}\n{comment.metadata['reply']}\n{'='*50}"
                for idx, comment in enumerate(example_comments)
            ])

            example_posts = query_index("x-posts-markus-odenthal", tweet).matches
            example_posts_str = "\n".join([
                f"Post: {idx + 1}\n{post.metadata['text']}\n{'-'*50}"
                for idx, post in enumerate(example_posts)
            ])

            ideas = current_app.config['viral_social_media_comments_ideas_chain'].invoke(
                {
                    "AUDIENCE_INFO": current_app.config['AUDIENCE'],
                    "PERSONAL_INFORMATION": current_app.config['PERSONAL_INFORMATION'],
                    "PREVIOUS_POSTS": example_posts_str,
                    "EXAMPLE_COMMENTS": example_comments_str,
                    "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
                    "POST_TO_COMMENT_ON": tweet,
                }
            )

            final_comment = current_app.config['viral_social_media_comments_refine_chain'].invoke(
                {
                    "AUDIENCE_INFO": current_app.config['AUDIENCE'],
                    "PERSONAL_INFORMATION": current_app.config['PERSONAL_INFORMATION'],
                    "EXAMPLE_COMMENTS": example_comments_str,
                    "PREVIOUS_POSTS": example_posts_str,
                    "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
                    "POST_TO_REPLY": tweet,
                    "COPYWRITING_STYLE": current_app.config['COPYWRITING_STYLE'],
                    "REPLY_IDEAS": ideas,
                }
            )
            final_reply = final_comment["root"][1]["final_reply"]
            return {"final_reply": final_reply}

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