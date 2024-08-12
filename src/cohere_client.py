import logging
import os
from modal import App, Image, Secret

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

image = Image.debian_slim(python_version="3.11").pip_install("cohere", "langsmith")
with image.imports():
    import cohere
    from langsmith import Client, traceable
    from langsmith.run_helpers import get_current_run_tree

app = App("cohere", image=image, secrets=[Secret.from_name("SocialMediaManager")])


@app.function()
def topic_classification(post: str) -> str:
    ls_client = Client()
    co = cohere.Client(os.getenv("COHERE_API_KEY"))

    @traceable(run_type="chain", name="topic_classification")
    def helper(post: str) -> str:
        response = co.classify(
            model="dd74f49b-dfcb-45fc-ac5f-bafa23eff44b-ft", inputs=[post]
        )
        prediction = response.classifications[0].prediction
        confidence = response.classifications[0].confidence

        run = get_current_run_tree()
        run_id = run.id
        ls_client.create_feedback(
            run_id,
            key="confidence",
            score=confidence,
        )
        return prediction

    logger.info("Starting topic classification")
    prediction = helper(post)
    logger.info("Topic classification completed")
    return prediction

@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    topic_classification.local("This is a test post")
    logger.info("Test function completed")