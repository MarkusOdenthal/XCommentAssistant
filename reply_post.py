from x.x import initialize_twitter_client, get_user_id, get_user_replies, get_original_posts, filter_level1_interactions
from semantic_search.upsert_pinecone import upsert_data
import re

def remove_username_mention(text):
    return re.sub(r'^@\S+\s*', '', text)

def main():
    client = initialize_twitter_client()
    username = "markusodenthal"
    user_id = get_user_id(client, username)
    
    if user_id:
        replies = get_user_replies(client, user_id)
        original_posts = get_original_posts(client, replies)
        level1_interactions = filter_level1_interactions(replies, original_posts, user_id)
        
        # Now you can analyze level1_interactions
        data = []
        for interaction in level1_interactions:
            metadata = {}
            metadata["original_post"] = interaction["original_post"].text
            metadata["original_post_id"] = interaction["original_post"].id
            metadata["original_post_author_id"] = interaction["original_post"].author_id
            metadata["original_post_created_at"] = interaction["original_post"].created_at.isoformat()
            # Unpack the original_post_metrics dictionary into metadata
            original_post_metrics = interaction["original_post"].public_metrics
            metadata.update({f"original_post_{k}": v for k, v in original_post_metrics.items()})
            metadata["reply"] = remove_username_mention(interaction["reply"].text)
            metadata["reply_id"] = interaction["reply"].id
            metadata["reply_created_at"] = interaction["reply"].created_at.isoformat()
            # Combine public and non-public reply metrics and unpack into metadata
            reply_metrics = {**interaction["reply"].public_metrics, **interaction["reply"].non_public_metrics}
            metadata.update({f"reply_{k}": v for k, v in reply_metrics.items()})

            data.append({
                "id": str(interaction['reply'].id),
                "text": interaction["original_post"].text,
                "metadata": metadata
            })
        upsert_data("x-comments-markus-odenthal", data)

if __name__ == "__main__":
    main()