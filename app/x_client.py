import datetime
import logging
import os
from collections import defaultdict
from typing import Dict, List, Tuple

import tweepy
from tweepy import Tweet

logger = logging.getLogger(__name__)


def initialize_twitter_client() -> tweepy.Client:
    required_env_vars = [
        "X_BEARER_TOKEN",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
        "X_ACCESS_CONSUMER_KEY",
        "X_ACCESS_CONSUMER_SECRET",
    ]
    missing_vars = [var for var in required_env_vars if os.getenv(var) is None]
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

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
        return {"error": f"RequestException: {e}"}


def get_user_posts(
    client: tweepy.Client, user_id: int, max_post_id: int, end_time=None
) -> List[tweepy.Tweet]:
    all_posts = []
    pagination_token = None
    try:
        while True:
            user_tweets = client.get_users_tweets(
                user_auth=True,
                id=user_id,
                end_time=end_time,
                max_results=100,
                since_id=max_post_id,
                tweet_fields=[
                    "created_at",
                    "public_metrics",
                    "conversation_id",
                    "non_public_metrics",
                ],
                pagination_token=pagination_token,
                expansions=["referenced_tweets.id", "in_reply_to_user_id"],
            )

            if user_tweets.data:
                all_posts.extend(user_tweets.data)

            pagination_token = user_tweets.meta.get("next_token", None)
            if not pagination_token:
                break

        return all_posts
    except tweepy.TweepyException as e:
        return {"error": f"RequestException: {e}"}


def get_user_replies(
    client: tweepy.Client, user_id: int, max_reply_id: int
) -> List[tweepy.Tweet]:
    all_replies = []
    pagination_token = None

    end_time = datetime.datetime.now() - datetime.timedelta(days=5)
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

            if user_tweets.meta["result_count"] == 0:
                break
            else:
                pagination_token = user_tweets.meta.get("next_token", None)
                replies = [
                    tweet
                    for tweet in user_tweets.data
                    if tweet.referenced_tweets
                    and tweet.referenced_tweets[0].type == "replied_to"
                ]
                all_replies.extend(replies)
        return all_replies

    except tweepy.TweepyException as e:
        return {"error": f"RequestException: {e}"}


def fetch_full_thread(client: tweepy.Client, tweet_id: int):
    thread = []
    current_tweet = client.get_tweet(
        tweet_id,
        tweet_fields=[
            "created_at",
            "public_metrics",
            "conversation_id",
            "in_reply_to_user_id",
        ],
        expansions=["referenced_tweets.id", "author_id"],
    ).data
    while current_tweet:
        thread.append(current_tweet)
        if current_tweet.referenced_tweets:
            current_tweet = client.get_tweet(
                current_tweet.referenced_tweets[0].id,
                tweet_fields=[
                    "created_at",
                    "public_metrics",
                    "conversation_id",
                    "in_reply_to_user_id",
                ],
                expansions=["referenced_tweets.id", "author_id"],
            ).data
        else:
            current_tweet = None
    thread.reverse()
    return thread


def get_original_posts(
    client: tweepy.Client, replies: List[tweepy.Tweet]
) -> List[tweepy.Tweet]:
    original_post_ids = [reply.referenced_tweets[0].id for reply in replies]
    original_posts = []
    missing_tweet_ids_list = []

    def fetch_tweets_in_chunks(ids_chunk):
        try:
            response = client.get_tweets(
                ids=ids_chunk,
                expansions=["referenced_tweets.id", "author_id"],
                tweet_fields=["created_at", "public_metrics", "conversation_id"],
            )
            missing_tweet_ids = [
                int(error["value"])
                for error in response.errors
                if "Could not find tweet with ids" in error["detail"]
            ]
            return response.data, missing_tweet_ids
        except tweepy.TweepyException as e:
            return {"error": f"RequestException: {e}"}

    chunk_size = 100
    for i in range(0, len(original_post_ids), chunk_size):
        ids_chunk = original_post_ids[i : i + chunk_size]
        tweets, missing_tweet_ids = fetch_tweets_in_chunks(ids_chunk)
        missing_tweet_ids_list.extend(missing_tweet_ids)

        for tweet in tweets:
            if (
                "in_reply_to_status_id" in tweet.data
                and tweet.data["in_reply_to_status_id"] is not None
            ):
                thread = fetch_full_thread(tweet.id)
                original_posts.append(thread)
            else:
                original_posts.append(tweet)

    return original_posts, missing_tweet_ids_list


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
