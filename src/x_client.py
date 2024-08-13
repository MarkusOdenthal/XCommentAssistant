import datetime
import logging
import os
from collections import defaultdict
from typing import Dict, List, Tuple

import modal
from modal.functions import FunctionCall

image = modal.Image.debian_slim(python_version="3.11").pip_install("tweepy")
with image.imports():
    import tweepy

app = modal.App(
    "x_client", image=image, secrets=[modal.Secret.from_name("SocialMediaManager")]
)


logger = logging.getLogger(__name__)


@app.cls()
class XClient:
    @modal.enter()
    def connect(self):
        self.client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
            consumer_key=os.getenv("X_ACCESS_CONSUMER_KEY"),
            consumer_secret=os.getenv("X_ACCESS_CONSUMER_SECRET"),
            wait_on_rate_limit=True,
        )
        return self.client

    @modal.method()
    def get_user_id(self, username: str) -> int:
        client = self.client
        try:
            return client.get_user(username=username).data.id
        except tweepy.TweepyException as e:
            return {"error": f"RequestException: {e}"}

    @modal.method()
    def get_user_info(self, username=None, user_id=None):
        client = self.client
        try:
            if username:
                return client.get_user(
                    username=username, user_fields=["description"]
                ).data
            elif user_id:
                return client.get_user(id=user_id, user_fields=["description"]).data
        except tweepy.TweepyException as e:
            return {"error": f"RequestException: {e}"}

    @modal.method()
    def get_user_posts(self, user_id: int, max_post_id: int, end_time=None):
        client = self.client
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
                        "note_tweet",
                    ],
                    pagination_token=pagination_token,
                    expansions=["referenced_tweets.id", "in_reply_to_user_id"],
                )

                if user_tweets.data:
                    for tweet in user_tweets.data:
                        note_tweet = tweet["data"].get("note_tweet", None)
                        if note_tweet:
                            tweet_text = note_tweet["text"]
                            logger.info(f"Processed longform tweet: {str(tweet.id)}")
                        else:
                            tweet_text = tweet.text
                            logger.info(f"Processed tweet: {str(tweet.id)}")
                        # Convert complex objects to dictionaries or primitive types
                        tweet_dict = {
                            "id": tweet.id,
                            "text": tweet_text,
                            "author_id": tweet.author_id,
                            "created_at": tweet.created_at.isoformat()
                            if tweet.created_at
                            else None,
                            "public_metrics": dict(tweet.public_metrics)
                            if tweet.public_metrics
                            else None,
                            "conversation_id": tweet.conversation_id,
                            "non_public_metrics": dict(tweet.non_public_metrics)
                            if tweet.non_public_metrics
                            else None,
                            "referenced_tweets": [
                                dict(ref) for ref in tweet.referenced_tweets
                            ]
                            if tweet.referenced_tweets
                            else None,
                            "in_reply_to_user_id": tweet.in_reply_to_user_id,
                        }
                        all_posts.append(tweet_dict)

                pagination_token = user_tweets.meta.get("next_token", None)
                if not pagination_token:
                    break

            return all_posts
        except tweepy.TweepyException as e:
            return {"error": f"RequestException: {e}"}

    @modal.method()
    def fetch_full_thread(self, tweet_id: int):
        client = self.client
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
            # Convert the tweet object to a dictionary
            tweet_dict = {
                "id": current_tweet.id,
                "text": current_tweet.text,
                "created_at": current_tweet.created_at.isoformat()
                if current_tweet.created_at
                else None,
                "public_metrics": dict(current_tweet.public_metrics)
                if current_tweet.public_metrics
                else None,
                "conversation_id": current_tweet.conversation_id,
                "in_reply_to_user_id": current_tweet.in_reply_to_user_id,
                "referenced_tweets": [
                    dict(ref) for ref in current_tweet.referenced_tweets
                ]
                if current_tweet.referenced_tweets
                else None,
                "author_id": current_tweet.author_id,
            }
            thread.append(tweet_dict)

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

    @modal.method()
    def get_original_posts(self, replies):
        client = self.client
        original_post_ids = [reply["referenced_tweets"][0]["id"] for reply in replies]
        original_posts = []
        missing_tweet_ids_list = []

        def fetch_tweets_in_chunks(ids_chunk):
            try:
                response = client.get_tweets(
                    ids=ids_chunk,
                    expansions=["referenced_tweets.id", "author_id"],
                    tweet_fields=["created_at", "public_metrics", "conversation_id", "note_tweet"],
                )
                missing_tweet_ids = [
                    int(error["value"])
                    for error in response.errors
                    if "Could not find tweet with ids" in error["detail"]
                ]
                return response.data, missing_tweet_ids
            except tweepy.TweepyException as e:
                return {"error": f"RequestException: {e}"}, []

        chunk_size = 100
        for i in range(0, len(original_post_ids), chunk_size):
            ids_chunk = original_post_ids[i : i + chunk_size]
            tweets, missing_tweet_ids = fetch_tweets_in_chunks(ids_chunk)
            missing_tweet_ids_list.extend(missing_tweet_ids)

            for tweet in tweets:
                note_tweet = tweet["data"].get("note_tweet", None)
                if note_tweet:
                    tweet_text = note_tweet["text"]
                    logger.info(f"Processed longform tweet: {str(tweet.id)}")
                else:
                    tweet_text = tweet.text
                    logger.info(f"Processed tweet: {str(tweet.id)}")
                tweet_dict = {
                    "id": tweet.id,
                    "text": tweet_text,
                    "created_at": tweet.created_at.isoformat()
                    if tweet.created_at
                    else None,
                    "public_metrics": dict(tweet.public_metrics)
                    if tweet.public_metrics
                    else None,
                    "conversation_id": tweet.conversation_id,
                    "in_reply_to_user_id": tweet.in_reply_to_user_id,
                    "referenced_tweets": [dict(ref) for ref in tweet.referenced_tweets]
                    if tweet.referenced_tweets
                    else None,
                    "author_id": tweet.author_id,
                }

                if (
                    "in_reply_to_status_id" in tweet_dict
                    and tweet_dict["in_reply_to_status_id"] is not None
                ):
                    thread = self.fetch_full_thread(tweet.id)
                    original_posts.append(thread)
                else:
                    original_posts.append(tweet_dict)

        return original_posts, missing_tweet_ids_list

    @modal.method()
    def get_list_tweets(self, list_id: str, latest_post_id: int):
        client = self.client
        if not isinstance(client, tweepy.Client):
            raise ValueError(
                "Provided client is not a valid tweepy.Client instance, expected tweepy.Client"
            )
        if not isinstance(list_id, str) or not list_id.strip():
            raise ValueError("Provided list_id is not a valid non-empty string")
        all_tweets = []
        pagination_token = None

        try:
            while True:
                list_tweets = client.get_list_tweets(
                    id=list_id,
                    max_results=10,
                    expansions=[
                        "attachments.media_keys",
                        "referenced_tweets.id",
                        "author_id",
                    ],
                    tweet_fields=[
                        "created_at",
                        "public_metrics",
                        "conversation_id",
                        "author_id",
                        "in_reply_to_user_id",
                        "attachments",
                        "note_tweet"
                    ],
                    media_fields=["url", "type"],
                    user_fields=["username", "description", "id"],
                    pagination_token=pagination_token,
                    user_auth=True,
                )
                # Extract tweets and user information from the response
                list_tweet_data = list_tweets.data
                if list_tweet_data is None:
                    return None, None
                

                # Convert users to dictionaries
                users = {
                    user["id"]: {
                        "id": user["id"],
                        "username": user["name"],
                        "description": user.get("description", "")
                    }
                    for user in list_tweets.includes["users"]
                }
                # media = {media["media_key"]: media for media in list_tweets.includes["media"]}
                # to get images I need to use this: list_tweets.includes and match this then to the media id.
                # all this new feature I also need then to add to the tweet/reply processing. (tweets to database)
                # Filter out all post with media:
                list_tweet_data = [
                    tweet for tweet in list_tweet_data if not tweet.attachments
                ]
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
            # can I move this part to the process tweets function? Is it already implemnted?
            all_tweets_clean = []
            for tweet in all_tweets:
                if tweet.referenced_tweets is None or (
                    tweet.referenced_tweets[0].type == "replied_to"
                    and tweet.in_reply_to_user_id == tweet.author_id
                ):
                    all_tweets_clean.append(tweet)
            # need refinement
            all_tweets_clean = self.process_tweets.local(
                all_tweets_clean, latest_post_id
            )[0]
            return all_tweets_clean, users
        except tweepy.TweepyException as e:
            logging.error(
                f"Error fetching list tweets for list {list_id} with pagination token {pagination_token} and latest_post_id {latest_post_id}: {e}"
            )
            return []

    @modal.method()
    def process_tweets(
        self, tweets, latest_post_id: int = None
    ) -> Tuple[List[Dict], int]:
        # Group tweets by conversation_id
        threads = defaultdict(list)
        new_latest_post_id = latest_post_id

        for tweet in tweets:
            try:
                threads[tweet["conversation_id"]].append(tweet)
                if new_latest_post_id is None or tweet["id"] > new_latest_post_id:
                    new_latest_post_id = tweet["id"]
            except AssertionError:
                logging.error("Tweet attributes missing or improperly formatted")
            if new_latest_post_id is None or tweet["id"] > new_latest_post_id:
                new_latest_post_id = tweet["id"]

        processed_tweets = []

        for conversation_id, thread_tweets in threads.items():
            try:
                sorted_tweets = sorted(
                    thread_tweets, key=lambda x: x["id"], reverse=True
                )
            except Exception as e:
                logging.error(
                    f"Error sorting tweets for conversation {conversation_id}: {e}"
                )
                continue
            
            # threads with more than one tweet
            if len(sorted_tweets) > 1:
                combined_text = "\n\n".join(
                    tweet["text"] for tweet in reversed(sorted_tweets)
                )
                combined_metrics = defaultdict(int)

                for tweet in sorted_tweets:
                    for metric, value in tweet["public_metrics"].items():
                        combined_metrics[metric] += value
                    if tweet["non_public_metrics"]:
                        for metric, value in tweet["non_public_metrics"].items():
                            combined_metrics[metric] += value

                processed_tweet = {
                    "conversation_id": conversation_id,
                    "text": combined_text,
                    "created_at": sorted_tweets[0]["created_at"],
                    "metrics": dict(combined_metrics),
                    "tweet_ids": [str(tweet["id"]) for tweet in sorted_tweets],
                    "is_thread": True,
                    "author_id": sorted_tweets[0]["author_id"],
                }
                logger.info(f"Processed thread: {str(sorted_tweets[0]['id'])}")
            # tweets and longform tweets
            else:
                tweet = sorted_tweets[0]
                all_metrics = {**tweet["public_metrics"]}
                if tweet["non_public_metrics"]:
                    all_metrics.update(tweet["non_public_metrics"])
                
                note_tweet = tweet["data"].get("note_tweet", None)
                if note_tweet:
                    text = tweet["data"]["note_tweet"]["text"]
                    logger.info(f"Note tweet: {str(tweet['id'])}")
                else:
                    text = tweet["text"]
                    logger.info(f"Processed tweet: {str(tweet['id'])}")
                processed_tweet = {
                    "conversation_id": conversation_id,
                    "text": text,
                    "created_at": tweet["created_at"],
                    "metrics": all_metrics,
                    "tweet_ids": [str(tweet["id"])],
                    "is_thread": False,
                    "author_id": tweet["author_id"],
                }

            processed_tweets.append(processed_tweet)
        processed_tweets.sort(key=lambda x: int(x["tweet_ids"][0]), reverse=True)

        tweets_clean = []
        for tweet in processed_tweets:
            metadata = {
                "text": tweet["text"],
                "created_at": tweet["created_at"],
                "is_thread": tweet["is_thread"],
                **tweet["metrics"],
                "author_id": tweet["author_id"],
            }
            tweets_clean.append(
                {
                    "id": tweet["tweet_ids"][0],
                    "text": tweet["text"],
                    "metadata": metadata,
                }
            )

        return tweets_clean, new_latest_post_id

    @modal.method()
    def process_replies_for_upload(
        self, replies, replies_original_post, latest_post_id
    ):
        import re

        def remove_username_mention(text):
            return re.sub(r"^@\S+\s*", "", text)

        data = []
        for reply, original_post in zip(replies, replies_original_post):
            metadata = {}
            metadata["original_post"] = original_post["text"]
            metadata["original_post_id"] = original_post["id"]
            metadata["original_post_author_id"] = original_post["author_id"]
            metadata["original_post_created_at"] = original_post["created_at"]
            original_post_metrics = original_post["public_metrics"]
            metadata.update(
                {f"original_post_{k}": v for k, v in original_post_metrics.items()}
            )
            metadata["reply"] = remove_username_mention(reply["text"])
            metadata["reply_id"] = reply["id"]
            metadata["reply_created_at"] = reply["created_at"]
            reply_metrics = {
                **reply["public_metrics"],
                **reply["non_public_metrics"],
            }
            metadata.update({f"reply_{k}": v for k, v in reply_metrics.items()})
            data.append(
                {
                    "id": str(reply["id"]),
                    "text": reply["text"],
                    "metadata": metadata,
                }
            )
            if latest_post_id is None or reply["id"] > latest_post_id:
                latest_post_id = reply["id"]
        return data, latest_post_id

    @modal.method()
    def get_all_post_replies_from_user(
        self, latest_post_id: int, username: str
    ) -> Dict:
        user_id = self.get_user_id.local(username=username)
        print(f"User ID: {user_id}")

        end_time = datetime.datetime.now() - datetime.timedelta(days=5)
        posts = self.get_user_posts.local(user_id, latest_post_id, end_time)
        print(f"Number of posts: {len(posts)}")

        if posts == []:
            return {"tweets": [], "replies": [], "latest_post_id": []}

        tweets = []
        replies = []

        for post in posts:
            if (
                post["in_reply_to_user_id"] == user_id
                or post["in_reply_to_user_id"] is None
            ):
                tweets.append(post)
            else:
                replies.append(post)
        print(f"Number of tweets: {len(tweets)}")
        print(f"Number of replies: {len(replies)}")

        replies_original_post, missing_tweet_ids_list = self.get_original_posts.local(
            replies
        )

        replies = [
            reply
            for reply in replies
            if reply["referenced_tweets"][0]["id"] not in missing_tweet_ids_list
        ]

        replies_for_upsert, latest_post_id = self.process_replies_for_upload.local(
            replies, replies_original_post, latest_post_id
        )
        tweets_for_upsert, new_latest_post_id = self.process_tweets.local(
            tweets, latest_post_id
        )
        return {
            "tweets": tweets_for_upsert,
            "replies": replies_for_upsert,
            "latest_post_id": new_latest_post_id,
        }

    @app.local_entrypoint()
    def test():
        post_replies = XClient().get_all_post_replies_from_user.local(
            0, "markusodenthal"
        )
        #all_tweets_clean, users = XClient().get_list_tweets.local("1821152727704994292", 1823402311349150034)
        return None


@app.function()
def accept_job(latest_post_id: int, username: str):
    call = XClient().get_all_post_replies_from_user.spawn(latest_post_id, username)
    return call.object_id


@app.function()
def accept_job_x_list(list_id: str, latest_post_id: int):
    call = XClient().get_list_tweets.spawn(list_id, latest_post_id)
    return call.object_id


@app.function()
def get_job_result_endpoint(call_id: str):
    function_call = FunctionCall.from_id(call_id)
    try:
        result = function_call.get(timeout=0)
    except TimeoutError:
        return {"result": "", "status_code": 202}

    return {"result": result, "status_code": 200}
