from app.x_client import get_list_tweets, initialize_twitter_client, process_tweets
import json
import traceback

try:
    with open("instance/data.json", "r") as file:
        data = json.load(file)
except (FileNotFoundError, json.JSONDecodeError):
    print(f"Error reading JSON file: {traceback.format_exc()}")
    data = {"max_post_id": 0}
for username, user_data in data["users"].items():
    lists = user_data.get("lists", 0)
    for list_name, list_data in lists.items():
        list_id = list_data.get("id", 0)
        latest_post_id = list_data.get("latest_post_id", 0)
        if latest_post_id is not None:
            latest_post_id += 1
        else:
            latest_post_id = 0
        client = initialize_twitter_client()
        tweets = get_list_tweets(client, list_id, latest_post_id)
        tweets = process_tweets(tweets)
        # ok this works.

        # next exlude all post that have media.
        # then implement everything in my pipeline so I get the new comment pipeline.
        # Next work on the image processing
        # Then longwork
        # then retweets

        # After this I can then direct start with image processing
        


