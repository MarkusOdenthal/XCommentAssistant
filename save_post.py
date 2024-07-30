from x.x import initialize_twitter_client, get_user_id, get_user_posts
from semantic_search.upsert_pinecone import upsert_data


def main(max_post_id):
    client = initialize_twitter_client()
    username = "markusodenthal"
    user_id = get_user_id(client, username)
    
    if user_id:
        posts = get_user_posts(client, user_id, max_post_id)
        
        # Now you can analyze level1_interactions
        data = []
        
        for post in posts:
            metadata = {}
            metadata["text"] = post.text
            metadata["created_at"] = post.created_at.isoformat()
            metrics = {**post.public_metrics, **post.non_public_metrics}
            metadata.update({k: v for k, v in metrics.items()})

            data.append({
                "id": str(post.id),
                "text": post.text,
                "metadata": metadata
            })

            # Track the maximum post.id
            if max_post_id is None or post.id > max_post_id:
                max_post_id = post.id

        upsert_data("x-posts-markus-odenthal", data)
        print(f"Max post.id: {max_post_id}")

if __name__ == "__main__":
    max_post_id = 1817953477068464583
    max_post_id += 1
    main(max_post_id)
