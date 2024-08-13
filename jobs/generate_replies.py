from modal import App, Volume, Cron, Function
import logging
import pathlib
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = App("generate_replies_job")


instance = Volume.from_name("instance")
VOL_MOUNT_PATH = pathlib.Path("/instance")

@app.function(
    schedule=Cron("0 2 * * *"),
    volumes={VOL_MOUNT_PATH: instance},
)
def generate_replies():
    try:
        read_data = Function.lookup("datastore", "read_data")
        save_data = Function.lookup("datastore", "save_data")
        accept_job_x_list = Function.lookup("x_client", "accept_job_x_list")
        get_job_result_endpoint = Function.lookup("x_client", "get_job_result_endpoint")
        topic_classification = Function.lookup("cohere", "topic_classification")
        generate_reply = Function.lookup("reply_pipeline", "generate_reply")
        send_message = Function.lookup("slack", "send_message")
    except Exception as e:
        logger.exception(f"Function lookup failed: {str(e)}")
        return
    data = read_data.remote()
    engagement_list = data['users']['markusodenthal']['lists']['Increase Engagement']
    slack_channel_id = engagement_list['slack_channel_id']
    list_id = engagement_list['id']
    # latest_post_id = engagement_list['latest_post_id']
    latest_post_id = 1823354970827067787

    call_id = accept_job_x_list.remote(list_id=list_id, latest_post_id=latest_post_id)
    time.sleep(10)
    results = get_job_result_endpoint.remote(call_id=call_id)
    max_retries = 5
    retry_count = 0
    while results["status_code"] == 202:
        print("Job not ready yet, waiting before retrying...")
        time.sleep(30)
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
        user = users.get(author_id)
        user_name = user.get("username")
        user_description = user.get("description")
        reply, example_comment = generate_reply.remote(tweet=tweet_text, user_name=user_name, user_description=user_description)
        # send reply to slack
        send_message.remote(
            # add here channel id from file.
            channel_id=slack_channel_id,
            author_id=author_id,
            post_id=tweet_id,
            final_reply=reply,
            example_comment=example_comment,
        )
    engagement_list['latest_post_id'] = latest_post_id
    save_data.remote(data)
    return None

# third craft the reply -> use the render server (will move this later)
    # what could be an simple implementation to optimize the retrieval part to get better information?
        # use DSPY and groq to improve the retrieval simple. Find ideas from strom how to do this: 
        # This is an nice notebook: https://colab.research.google.com/github/stanfordnlp/dspy/blob/main/examples/tweets/tweets_assertions.ipynb
        # If I'm able to implement this I could the optimise this pipeline with real time data from X. 
    # find similar tweets <-> comments
    # find similar own tweets
    # create first 3 ideas
    # create final reply

# define entry point for the job -> schedule every 15 minutes
@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    generate_replies.local()
    logger.info("Test function completed")
