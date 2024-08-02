import datetime
import os
from typing import Dict, List

import tweepy
import logging

logger = logging.getLogger(__name__)

def initialize_twitter_client() -> tweepy.Client:
    required_env_vars = [
        "X_BEARER_TOKEN",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
        "X_ACCESS_CONSUMER_KEY",
        "X_ACCESS_CONSUMER_SECRET"
    ]
    missing_vars = [var for var in required_env_vars if os.getenv(var) is None]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return tweepy.Client(
        bearer_token=os.getenv("X_BEARER_TOKEN"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
        consumer_key=os.getenv("X_ACCESS_CONSUMER_KEY"),
        consumer_secret=os.getenv("X_ACCESS_CONSUMER_SECRET"),
        wait_on_rate_limit=True,
    )


def get_user_id(client: tweepy.Client, username: str) -> int:
    try:
        return client.get_user(username=username).data.id
    except tweepy.TweepyException as e:
        return {'error': f'RequestException: {e}'}


def get_user_info(client: tweepy.Client, username=None, user_id=None) -> tweepy.User:
    try:
        if username:
            return client.get_user(
                screen_name=username, user_fields=["description"]
            ).data
        elif user_id:
            return client.get_user(id=user_id, user_fields=["description"]).data
    except tweepy.TweepyException as e:
        return {'error': f'RequestException: {e}'}


def get_user_posts(
    client: tweepy.Client, user_id: int, max_post_id: int
) -> List[tweepy.Tweet]:
    all_posts = []
    pagination_token = None

    try:
        while True:
            user_tweets = client.get_users_tweets(
                user_auth=True,
                id=user_id,
                max_results=100,
                since_id=max_post_id,
                exclude=["replies"],
                tweet_fields=[
                    "created_at",
                    "public_metrics",
                    "conversation_id",
                    "non_public_metrics",
                ],
                pagination_token=pagination_token,
            )

            if user_tweets.data:
                all_posts.extend(user_tweets.data)

            pagination_token = user_tweets.meta.get("next_token", None)
            if not pagination_token:
                break

        return all_posts
    except tweepy.TweepyException as e:
        return {'error': f'RequestException: {e}'}


def get_user_replies(
    client: tweepy.Client, user_id: int, max_reply_id: int
) -> List[tweepy.Tweet]:
    all_replies = []
    pagination_token = None

    end_time = datetime.datetime.now() - datetime.timedelta(days=3)
    try:
        while True:
            user_tweets = client.get_users_tweets(
                user_auth=True,
                id=user_id,
                max_results=100,
                end_time=end_time,
                since_id=max_reply_id,  # hard set when run the first time for client
                exclude=["retweets"],
                expansions=["referenced_tweets.id"],
                tweet_fields=[
                    "created_at",
                    "public_metrics",
                    "conversation_id",
                    "non_public_metrics",
                ],
                pagination_token=pagination_token,
            )

            if user_tweets.data:
                replies = [
                    tweet
                    for tweet in user_tweets.data
                    if tweet.referenced_tweets
                    and tweet.referenced_tweets[0].type == "replied_to"
                ]
                all_replies.extend(replies)

            pagination_token = user_tweets.meta.get("next_token", None)
            if not pagination_token:
                break

        return all_replies

    except tweepy.TweepyException as e:
        return {'error': f'RequestException: {e}'}



def get_original_posts(
    client: tweepy.Client, replies: List[tweepy.Tweet]
) -> Dict[int, tweepy.Tweet]:
    original_post_ids = [reply.referenced_tweets[0].id for reply in replies]
    original_posts = {}

    def fetch_tweets_in_chunks(ids_chunk):
        try:
            response = client.get_tweets(
                ids=ids_chunk,
                expansions=["referenced_tweets.id", "author_id"],
                tweet_fields=["created_at", "public_metrics", "conversation_id"],
            )
            return response.data
        except tweepy.TweepyException as e:
            return {'error': f'RequestException: {e}'}

    chunk_size = 100
    for i in range(0, len(original_post_ids), chunk_size):
        ids_chunk = original_post_ids[i : i + chunk_size]
        tweets = fetch_tweets_in_chunks(ids_chunk)
        original_posts.update({tweet.id: tweet for tweet in tweets})

    return original_posts


def filter_level1_interactions(
    replies: List[tweepy.Tweet], original_posts: Dict[int, tweepy.Tweet], user_id: int
) -> List[Dict]:
    level1_interactions = []
    for reply in replies:
        if not reply.referenced_tweets:
            continue
        try:
            original_post_id = reply.referenced_tweets[0].id
        except IndexError:
            continue
        original_post = original_posts.get(original_post_id)
        if not original_post:
            continue
        if original_post and original_post.referenced_tweets is None:
            level1_interactions.append({"original_post": original_post, "reply": reply})
    return level1_interactions


def get_tweet_statistics(client: tweepy.Client, tweet_url: str) -> Dict:
    # Extract tweet ID from URL
    tweet_id = tweet_url.split("/")[-1].split("?")[0]

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


def get_list_tweets(client: tweepy.Client, list_id: str) -> List[tweepy.Tweet]:
    if not isinstance(client, tweepy.Client):
        raise ValueError("Provided client is not a valid tweepy.Client instance")
    if not isinstance(list_id, str) or not list_id.strip():
        raise ValueError("Provided list_id is not a valid non-empty string")
    all_tweets = []
    pagination_token = None

    try:
        while True:
            list_tweets = client.get_list_tweets(
                id=list_id,
                max_results=20,
                expansions=["referenced_tweets.id", "attachments.media_keys"],
                tweet_fields=["created_at", "public_metrics", "conversation_id"],
                media_fields=["url", "type"],
                pagination_token=pagination_token,
                user_auth=True,
            )

            if list_tweets.data:
                all_tweets.extend(list_tweets.data)

            pagination_token = list_tweets.meta.get("next_token", None)
            if not pagination_token:
                break

        return all_tweets
    except tweepy.TweepyException as e:
        logging.error(f"Error fetching list tweets for list {list_id} with pagination token {pagination_token}: {e}")
        return []
