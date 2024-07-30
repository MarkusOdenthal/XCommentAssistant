import os
from typing import Dict, List

import tweepy


def initialize_twitter_client() -> tweepy.Client:
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
    except tweepy.TweepError as e:
        print(f"Error fetching user ID: {e}")
        return None


def get_user_info(client: tweepy.Client, username=None, user_id=None) -> tweepy.User:
    try:
        if username:
            return client.get_user(
                screen_name=username, user_fields=["description"]
            ).data
        elif user_id:
            return client.get_user(id=user_id, user_fields=["description"]).data
    except tweepy.TweepError as e:
        print(f"Error fetching user info: {e}")
        return None


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
    except tweepy.TweepError as e:
        print(f"Error fetching user tweets: {e}")
        return []


def get_user_replies(
    client: tweepy.Client, user_id: int, max_reply_id: int
) -> List[tweepy.Tweet]:
    all_replies = []
    pagination_token = None

    try:
        while True:
            user_tweets = client.get_users_tweets(
                user_auth=True,
                id=user_id,
                max_results=100,
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

    except tweepy.TweepError as e:
        print(f"Error fetching user tweets: {e}")
        return []


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
        except tweepy.TweepError as e:
            print(f"Error fetching original posts: {e}")
            return []

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
        original_post = original_posts.get(reply.referenced_tweets[0].id)
        if original_post and original_post.referenced_tweets is None:
            level1_interactions.append({"original_post": original_post, "reply": reply})
    return level1_interactions
