# app/topic_classification.py
from langsmith import Client, traceable
from langsmith.run_helpers import get_current_run_tree
from .cohere_client import co

ls_client = Client()

@traceable(
    run_type="chain",
    name="topic_classification",
)
def topic_classification(post: str):
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
