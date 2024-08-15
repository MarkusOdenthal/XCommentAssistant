import logging
import os
from modal import App, Image, Secret


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

image = Image.debian_slim(python_version="3.11").pip_install("cohere", "langsmith", "langchain")
with image.imports():
    import cohere
    from langsmith import Client
    from langsmith.run_trees import RunTree
    from uuid import uuid4
    from langchain.callbacks.tracers.langchain import wait_for_all_tracers

app = App("cohere", image=image, secrets=[Secret.from_name("SocialMediaManager")])


@app.function()
def topic_classification(post: str) -> str:
    api_key = os.getenv("COHERE_API_KEY")
    model_id = os.getenv("COHERE_MODEL_ID")
    if not api_key or not model_id:
        raise EnvironmentError("COHERE_API_KEY and COHERE_MODEL_ID must be set")
    logger.info("Starting topic classification")
    ls_client = Client()
    co = cohere.Client(api_key)
    model_id = os.getenv("COHERE_MODEL_ID")

    run_id = uuid4()
    pipeline = RunTree(
       name="topic_classification",
       run_type="chain",
       inputs={"post": post},
       id=run_id,
    )
    response = co.classify(
        model=model_id, inputs=[post]
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
    wait_for_all_tracers()
    logger.info("Topic classification completed")
    return prediction

@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    topic_classification.local("This is a test post")
    logger.info("Test function completed")