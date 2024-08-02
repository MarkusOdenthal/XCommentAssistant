import json

from app.pinecone_client import upsert_data
from app.x_client import get_user_id, get_user_posts, initialize_twitter_client


def main(latest_post_id: int)-> int:
    try:
        client = initialize_twitter_client()
    except EnvironmentError as e:
        print(f"Error initializing Twitter client: {e}")
        return None
    username = "markusodenthal"
    user_id = get_user_id(client, username)

    if user_id:
        posts = get_user_posts(client, user_id, latest_post_id)

        # Now you can analyze level1_interactions
        data = []

        for post in posts:
            metadata = {}
            metadata["text"] = post.text
            metadata["created_at"] = post.created_at.isoformat()
            metrics = {**post.public_metrics, **post.non_public_metrics}
            metadata.update({k: v for k, v in metrics.items()})

            data.append({"id": str(post.id), "text": post.text, "metadata": metadata})

            # Track the maximum post.id
            if latest_post_id is None or post.id > latest_post_id:
                new_post_id = post.id

        upsert_data("x-posts-markus-odenthal", data)
        return new_post_id


if __name__ == "__main__":
    try:
        with open("instance/data.json", "r") as file:
            max_post_id = json.load(file).get("max_post_id")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading JSON file: {e}")
        max_post_id = None
    if max_post_id is not None:
        max_post_id += 1
    else:
        max_post_id = 0
    max_post_id = main(max_post_id)
