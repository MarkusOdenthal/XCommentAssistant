import logging

import modal
from fastapi import Request

image = modal.Image.debian_slim(python_version="3.11").pip_install("langsmith")
with image.imports():
    from langsmith import Client

app = modal.App(
    "training_dataset", image=image, secrets=[modal.Secret.from_name("SocialMediaManager")]
)

logger = logging.getLogger(__name__)

@app.function()
def add_label_data_to_topic_classification(post, label):
    ls_client = Client()

    _ = ls_client.create_examples(
        inputs=[{"text": post}],
        outputs=[{"label": label}],
        dataset_name="XCommentClassification",
    )
    return {"message": "Example added successfully"}, 200


@app.function()
@modal.web_endpoint(method="POST")
async def add_label_data_endpoint(request: Request):
    payload = await request.json()
    post = payload.get("post")
    label = payload.get("label")
    
    if not post or not label:
        return {"error": "Missing 'post' or 'label' in request"}, 400
    
    response = add_label_data_to_topic_classification.local(post, label)
    return response