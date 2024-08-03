import json
import re

from app.pinecone_client import upsert_data
from app.x_client import (
    filter_level1_interactions,
    get_original_posts,
    get_user_id,
    get_user_replies,
    initialize_twitter_client,
)


def remove_username_mention(text):
    return re.sub(r"^@\S+\s*", "", text)


def main(max_reply_id):
    client = initialize_twitter_client()
    username = "markusodenthal"
    user_id = get_user_id(client, username)

    if user_id:
        replies = get_user_replies(client, user_id, max_reply_id)
        original_posts = get_original_posts(client, replies)
        level1_interactions = filter_level1_interactions(
            replies, original_posts, user_id
        )

        # Now you can analyze level1_interactions
        data = []

        for interaction in level1_interactions:
            metadata = {}
            metadata["original_post"] = interaction["original_post"].text
            metadata["original_post_id"] = interaction["original_post"].id
            metadata["original_post_author_id"] = interaction["original_post"].author_id
            metadata["original_post_created_at"] = interaction[
                "original_post"
            ].created_at.isoformat()
            # Unpack the original_post_metrics dictionary into metadata
            original_post_metrics = interaction["original_post"].public_metrics
            metadata.update(
                {f"original_post_{k}": v for k, v in original_post_metrics.items()}
            )
            metadata["reply"] = remove_username_mention(interaction["reply"].text)
            metadata["reply_id"] = interaction["reply"].id
            metadata["reply_created_at"] = interaction["reply"].created_at.isoformat()
            # Combine public and non-public reply metrics and unpack into metadata
            reply_metrics = {
                **interaction["reply"].public_metrics,
                **interaction["reply"].non_public_metrics,
            }
            metadata.update({f"reply_{k}": v for k, v in reply_metrics.items()})

            data.append(
                {
                    "id": str(interaction["reply"].id),
                    "text": interaction["original_post"].text,
                    "metadata": metadata,
                }
            )

            # Track the maximum post.id
            if max_reply_id is None or interaction["reply"].id > max_reply_id:
                max_reply_id = interaction["reply"].id

        upsert_data("x-comments-markus-odenthal", data)
        print(f"Adding {len(data)} comments to Pinecone")
        return max_reply_id


if __name__ == "__main__":
    try:
        with open('instance/data.json', 'r') as file:
            max_reply_id = json.load(file).get('max_reply_id')
    except (FileNotFoundError, PermissionError) as file_error:
        print(f"File error: {file_error}")
        max_reply_id = 0
    except json.JSONDecodeError as json_error:
        print(f"JSON error: {json_error}")
        max_reply_id = 0
    max_reply_id += 1
    max_reply_id = main(max_reply_id)
    with open("instance/data.json", "w") as file:
        json.dump({"max_reply_id": max_reply_id}, file, indent=4)
