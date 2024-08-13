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
    from langsmith import Client
    from langsmith.run_trees import RunTree
    from uuid import uuid4

app = App("cohere", image=image, secrets=[Secret.from_name("SocialMediaManager")])


@app.function()
def topic_classification(post: str) -> str:
    logger.info("Starting topic classification")
    ls_client = Client()
    co = cohere.Client(os.getenv("COHERE_API_KEY"))

    run_id = uuid4()
    pipeline = RunTree(
       name="topic_classification",
       run_type="chain",
       inputs={"post": post},
       id=run_id,
    )
    response = co.classify(
        model="dd74f49b-dfcb-45fc-ac5f-bafa23eff44b-ft", inputs=[post]
    )
    prediction = response.classifications[0].prediction
    confidence = response.classifications[0].confidence

    pipeline.end(outputs={"output": prediction})
    pipeline.post()
    ls_client.create_feedback(
        run_id,
        key="confidence",
        score=confidence,
    )
    logger.info("Topic classification completed")
    return prediction

@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    topic_classification.local("This is a test post")
    logger.info("Test function completed")