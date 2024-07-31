from x.x import initialize_twitter_client, get_user_id, get_user_replies, get_original_posts, filter_level1_interactions
from semantic_search.upsert_pinecone import upsert_data
import re


def remove_username_mention(text):
    return re.sub(r'^@\S+\s*', '', text)

def main(max_reply_id):
    client = initialize_twitter_client()
    username = "markusodenthal"
    user_id = get_user_id(client, username)
    
    if user_id:
        replies = get_user_replies(client, user_id, max_reply_id)
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

            # Track the maximum post.id
            if max_reply_id is None or interaction["reply"].id > max_reply_id:
                max_reply_id = interaction["reply"].id

        upsert_data("x-comments-markus-odenthal", data)

        print(f"Max reply.id: {max_reply_id}")

if __name__ == "__main__":
    max_reply_id = 1817247042105643500
    max_reply_id += 1
    main(max_reply_id)

# last reply id: 1817247042105643500
# Maybe print this always out and add then 1 to query the next day. But I need also to wait on day. 
# actually I could simply this. I can work with start_time and end_time. And could work with time windows. This way
# I could update not update data. I could make th