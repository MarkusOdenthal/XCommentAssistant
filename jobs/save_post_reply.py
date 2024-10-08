import logging
import time

from modal import App, Cron, Function

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = App("save_posts_replies_job")


@app.function(schedule=Cron("0 2 * * *"), timeout=7200,)
def save_post_reply():
    try:
        read_data = Function.lookup("datastore", "read_data")
        save_data = Function.lookup("datastore", "save_data")
        f_upsert = Function.lookup("pinecone", "upsert")
        f_accept_job = Function.lookup("x_client", "accept_job")
        f_get_job_result_endpoint = Function.lookup(
            "x_client", "get_job_result_endpoint"
        )
        f_embed = Function.lookup("openai_client", "embed")
    except Exception as e:
        logger.exception(f"Function lookup failed: {str(e)}")
        return

    data = read_data.remote()

    for username, user_data in data.get("users", {}).items():
        latest_post_id = user_data.get("latest_post_id", 0)
        logger.info(f"Latest post ID for {username}: {latest_post_id}")

        if latest_post_id is not None:
            latest_post_id += 1
        else:
            latest_post_id = 0
        call_id = f_accept_job.remote(latest_post_id=latest_post_id, username=username)
        results = f_get_job_result_endpoint.remote(call_id=call_id)
        max_retries = 5
        retry_count = 0
        while results["status_code"] == 202:
            print("Job not ready yet, waiting before retrying...")
            time.sleep(30)
            results = f_get_job_result_endpoint.remote(call_id=call_id)
            retry_count += 1
            if retry_count > max_retries:
                logger.error("Max retries exceeded. Exiting loop.")
                break
            # Placeholder for future implementation
            logger.info("Post processing completed. Ready to save data.")

        logger.info("Job completed, results received:")
        results = results["result"]

        # process tweets
        tweets = results["tweets"]
        if tweets:
            doc_embeds = [f_embed.remote(d["text"])[0] for d in tweets]
            vectors = []
            for d, e in zip(tweets, doc_embeds):
                vectors.append({"id": d["id"], "values": e, "metadata": d["metadata"]})
            f_upsert.remote(index_name="x-posts-markus-odenthal", vectors=vectors)
            logger.info(f"{len(vectors)} posts upserted successfully!")
        else:
            logger.info("No new posts to process.")

        # proess replies
        replies = results["replies"]
        if replies:
            doc_embeds = [f_embed.remote(d["text"])[0] for d in replies]
            vectors = []
            for d, e in zip(replies, doc_embeds):
                vectors.append({"id": d["id"], "values": e, "metadata": d["metadata"]})
            f_upsert.remote(index_name="x-comments-markus-odenthal", vectors=vectors)
            logger.info(f"{len(vectors)} comments upserted successfully!")
        else:
            logger.info("No new replies to process.")

        latest_post_id = results["latest_post_id"]
        logger.info(f"Last post ID: {results['latest_post_id']}")
        user_data["latest_post_id"] = latest_post_id

    save_data.remote(data)
    logger.info("Data saved successfully")
    return None


@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    save_post_reply.local()
    logger.info("Test function completed")
