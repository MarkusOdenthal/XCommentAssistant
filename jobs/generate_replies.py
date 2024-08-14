from modal import App, Cron, Function
import logging
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = App("generate_replies_job")

@app.function(
    schedule=Cron("*/5 6-21 * * *"),
    timeout=600
)
def generate_replies():
    read_data = Function.lookup("datastore", "read_data")
    save_data = Function.lookup("datastore", "save_data")
    accept_job_x_list = Function.lookup("x_client", "accept_job_x_list")
    get_job_result_endpoint = Function.lookup("x_client", "get_job_result_endpoint")
    topic_classification = Function.lookup("cohere", "topic_classification")
    generate_reply = Function.lookup("reply_pipeline", "generate_reply")
    send_message = Function.lookup("slack", "send_message")
    data = read_data.remote()
    x_lists = data['users']['markusodenthal']['lists']
    for list_name, list_data in x_lists.items():
        slack_channel_id = list_data['slack_channel_id']
        list_id = list_data['id']
        latest_post_id = list_data['latest_post_id']
    
        call_id = accept_job_x_list.remote(list_id=list_id, latest_post_id=latest_post_id)
        time.sleep(10)
        results = get_job_result_endpoint.remote(call_id=call_id)
        max_retries = 15
        retry_count = 0
        while results["status_code"] == 202:
            print("Job not ready yet, waiting before retrying...")
            time.sleep(60)
            results = get_job_result_endpoint.remote(call_id=call_id)
            retry_count += 1
            if retry_count > max_retries:
                logger.error("Max retries exceeded. Exiting loop.")
                break
            logger.info("Post processing completed. Ready to save data.")
        logger.info("Job completed, results received:")
        tweets, users = results["result"]

        for tweet in tweets:
            tweet_text = tweet.get("text")
            classification = topic_classification.remote(post=tweet_text)
            if classification != "interesting_topic":
                continue

            author_id = tweet["metadata"].get("author_id")
            tweet_id = int(tweet.get("id"))
            if tweet_id > latest_post_id:
                latest_post_id = tweet_id
                list_data['latest_post_id'] = latest_post_id
                save_data.remote(data)
            user = users.get(author_id)
            if user:
                user_name = user.get("username")
                user_description = user.get("description")
            else:
                logger.info(f"No user information available for author_id {author_id}")
                user_name = "No user information available"
                user_description = "No user information available"
            reply, example_comment = generate_reply.remote(tweet=tweet_text, user_name=user_name, user_description=user_description)
            send_message.remote(
                channel_id=slack_channel_id,
                author_id=author_id,
                post_id=tweet_id,
                final_reply=reply,
                example_comment=example_comment,
            )  
    return None

@app.local_entrypoint()
def test_function():
    """
    _summary_: This function is used to test the generate_replies function
    """
    logger.info("Starting test function")
    generate_replies.local()
    logger.info("Test function completed")
