import datetime
import json
import re
import traceback

from app.pinecone_client import upsert_data
from app.x_client import (
    get_original_posts,
    get_user_id,
    get_user_posts,
    initialize_twitter_client,
    process_tweets,
)


def remove_username_mention(text):
    return re.sub(r"^@\S+\s*", "", text)


def process_replies_for_upload(replies, replies_original_post, latest_post_id):
    data = []
    for reply, original_post in zip(replies, replies_original_post):
        metadata = {}
        metadata["original_post"] = original_post.text
        metadata["original_post_id"] = original_post.id
        metadata["original_post_author_id"] = original_post.author_id
        metadata["original_post_created_at"] = original_post.created_at.isoformat()
        # Unpack the original_post_metrics dictionary into metadata
        original_post_metrics = original_post.public_metrics
        metadata.update(
            {f"original_post_{k}": v for k, v in original_post_metrics.items()}
        )
        metadata["reply"] = remove_username_mention(reply.text)
        metadata["reply_id"] = reply.id
        metadata["reply_created_at"] = reply.created_at.isoformat()
        # Combine public and non-public reply metrics and unpack into metadata
        reply_metrics = {
            **reply.public_metrics,
            **reply.non_public_metrics,
        }
        metadata.update({f"reply_{k}": v for k, v in reply_metrics.items()})
        data.append(
            {
                "id": str(reply.id),
                "text": reply.text,
                "metadata": metadata,
            }
        )
        # Track the maximum post.id
        if latest_post_id is None or reply.id > latest_post_id:
            latest_post_id = reply.id
    if len(data) > 0:
        upsert_data("x-comments-markus-odenthal", data)
    print(f"Adding {len(data)} comments to Pinecone")
    return latest_post_id


def main(latest_post_id: int, username: str) -> int:
    try:
        client = initialize_twitter_client()
    except EnvironmentError as e:
        print(f"Error initializing Twitter client: {e}")
        return None
    user_id = get_user_id(client, username)

    if user_id:
        end_time = datetime.datetime.now() - datetime.timedelta(days=3)
        posts = get_user_posts(client, user_id, latest_post_id, end_time)

        # Now you can analyze level1_interactions
        data = []
        tweets = []
        replies = []

        for post in posts:
            if post.in_reply_to_user_id == user_id or post.in_reply_to_user_id is None:
                tweets.append(post)
            else:
                replies.append(post)

        # process replies
        replies_original_post, missing_tweet_ids_list = get_original_posts(
            client, replies
        )
        replies = [
            reply
            for reply in replies
            if reply.referenced_tweets[0].id not in missing_tweet_ids_list
        ]
        latest_post_id = process_replies_for_upload(
            replies, replies_original_post, latest_post_id
        )

        processed_tweets, new_latest_post_id = process_tweets(tweets, latest_post_id)
        data = []
        for tweet in processed_tweets:
            metadata = {
                "text": tweet["text"],
                "created_at": tweet["created_at"],
                "is_thread": tweet["is_thread"],
                **tweet["metrics"],
            }
            data.append(
                {
                    "id": tweet["tweet_ids"][0],
                    "text": tweet["text"],
                    "metadata": metadata,
                }
            )

        print(f"Adding {len(data)} posts to Pinecone")
        if len(data) > 0:
            upsert_data("x-posts-markus-odenthal", data)
        return new_latest_post_id


if __name__ == "__main__":
    try:
        with open("instance/data.json", "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Error reading JSON file: {traceback.format_exc()}")
        data = {"max_post_id": 0}

    for username, user_data in data["users"].items():
        latest_post_id = user_data.get("latest_post_id", 0)

        if latest_post_id is not None:
            latest_post_id += 1
        else:
            latest_post_id = 0

        new_post_id = main(latest_post_id, username)

        if new_post_id is not None:
            user_data["latest_post_id"] = new_post_id
        else:
            print("Error saving post")
    with open("instance/data.json", "w") as file:
        json.dump(data, file)
