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


def get_user_info(client: tweepy.Client, username=None, user_id=None) -> tweepy.User:
    try:
        if username:
            return client.get_user(
                screen_name=username, user_fields=["description"]
            ).data
        elif user_id:
            return client.get_user(id=user_id, user_fields=["description"]).data
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


def get_list_tweets(
    client: tweepy.Client, list_id: str, latest_post_id: int
) -> List[tweepy.Tweet]:
    if not isinstance(client, tweepy.Client):
        raise ValueError("Provided client is not a valid tweepy.Client instance, expected tweepy.Client")
    if not isinstance(list_id, str) or not list_id.strip():
        raise ValueError("Provided list_id is not a valid non-empty string")
    all_tweets = []
    pagination_token = None

    try:
        while True:
            list_tweets = client.get_list_tweets(
                id=list_id,
                max_results=100,
                expansions=["attachments.media_keys", "referenced_tweets.id", "author_id"],
                tweet_fields=["created_at", "public_metrics", "conversation_id", "author_id", "in_reply_to_user_id", "attachments"],
                media_fields=["url", "type"],
                user_fields=["username", "description", "id"],
                pagination_token=pagination_token,
                user_auth=True,
            )
            # Extract tweets and user information from the response
            list_tweet_data = list_tweets.data
            if list_tweet_data is None:
                return None, None
            users = {user["id"]: user for user in list_tweets.includes["users"]}
            # media = {media["media_key"]: media for media in list_tweets.includes["media"]}
            # to get images I need to use this: list_tweets.includes and match this then to the media id.
            # Filter out all post with media:
            list_tweet_data = [tweet for tweet in list_tweet_data if not tweet.attachments]
            tweet_ids = [tweet.id for tweet in list_tweet_data]
            min_tweet_id = min(tweet_ids)
            if min_tweet_id <= latest_post_id:
                list_tweet_data = [
                    tweet for tweet in list_tweet_data if tweet.id > latest_post_id
                ]
                all_tweets.extend(list_tweet_data)
                break
            else:
                all_tweets.extend(list_tweet_data)
                pagination_token = list_tweets.meta.get("next_token", None)
        all_tweets_clean = []
        for tweet in all_tweets:
            if tweet.referenced_tweets is None or (tweet.referenced_tweets[0].type == "replied_to" and tweet.in_reply_to_user_id == tweet.author_id):
                all_tweets_clean.append(tweet)
        return all_tweets_clean, users
    except tweepy.TweepyException as e:
        logging.error(
            f"Error fetching list tweets for list {list_id} with pagination token {pagination_token} and latest_post_id {latest_post_id}: {e}"
        )
        return []


def process_tweets(
    tweets: List[Tweet], latest_post_id: int = None
) -> Tuple[List[Dict], int]:
    # Group tweets by conversation_id
    threads = defaultdict(list)
    new_latest_post_id = latest_post_id

    for tweet in tweets:
        try:
            assert all(hasattr(tweet, attr) for attr in ['text', 'id', 'conversation_id', 'public_metrics', 'non_public_metrics', 'created_at'])
            threads[tweet.conversation_id].append(tweet)
            if new_latest_post_id is None or tweet.id > new_latest_post_id:
                new_latest_post_id = tweet.id
        except AssertionError:
            logging.error('Tweet attributes missing or improperly formatted')
        if new_latest_post_id is None or tweet.id > new_latest_post_id:
            new_latest_post_id = tweet.id

    processed_tweets = []

    for conversation_id, thread_tweets in threads.items():
        try:
            sorted_tweets = sorted(thread_tweets, key=lambda x: x.id, reverse=True)
        except Exception as e:
            logging.error(f'Error sorting tweets for conversation {conversation_id}: {e}')
            continue

        if len(sorted_tweets) > 1:
            combined_text = "\n\n".join(tweet.text for tweet in reversed(sorted_tweets))
            combined_metrics = defaultdict(int)

            for tweet in sorted_tweets:
                for metric, value in tweet.public_metrics.items():
                    combined_metrics[metric] += value
                if tweet.non_public_metrics:
                    for metric, value in tweet.non_public_metrics.items():
                        combined_metrics[metric] += value

            processed_tweet = {
                "conversation_id": conversation_id,
                "text": combined_text,
                "created_at": sorted_tweets[0].created_at.isoformat(),
                "metrics": dict(combined_metrics),
                "tweet_ids": [str(tweet.id) for tweet in sorted_tweets],
                "is_thread": True,
                "author_id": sorted_tweets[0].author_id,
            }
        else:
            tweet = sorted_tweets[0]
            all_metrics = {**tweet.public_metrics}
            if tweet.non_public_metrics:
                all_metrics.update(tweet.non_public_metrics)

            processed_tweet = {
                "conversation_id": conversation_id,
                "text": tweet.text,
                "created_at": tweet.created_at.isoformat(),
                "metrics": all_metrics,
                "tweet_ids": [str(tweet.id)],
                "is_thread": False,
                "author_id": tweet.author_id,
            }

        processed_tweets.append(processed_tweet)
    processed_tweets.sort(key=lambda x: int(x["tweet_ids"][0]), reverse=True)
    return processed_tweets, new_latest_post_id
