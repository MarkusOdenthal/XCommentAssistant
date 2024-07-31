from app.pinecone_client import query_index
from app.x_client import get_user_id, initialize_twitter_client

client = initialize_twitter_client()
username = "markusodenthal"
user_id = get_user_id(client, username)
post = """Successful people see opportunity in every failure. 

Normal people see failure in every opportunity. 

Both are right. One gets rich."""

results = query_index("x-comments-markus-odenthal", post).matches
results = [result for result in results if int(result['metadata']['original_post_author_id']) != user_id]
for idx, result in enumerate(results):
    print(f"Post: {1 + idx}")
    print(result.metadata['original_post'])
    print('-' * 50)
    print(f"Reply: {1 + idx}")
    print(result.metadata['reply'])
    print('=' * 50)