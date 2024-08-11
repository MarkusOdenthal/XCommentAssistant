import logging

import modal
import openai

image = modal.Image.debian_slim(python_version="3.11").pip_install("openai")
with image.imports():
    import os

    import openai

app = modal.App(
    "openai_client", image=image, secrets=[modal.Secret.from_name("SocialMediaManager")]
)

logger = logging.getLogger(__name__)


@app.function()
def embed(docs: list[str]) -> list[list[float]]:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    res = openai.embeddings.create(input=docs, model="text-embedding-3-small")
    doc_embeds = [r.embedding for r in res.data]
    return doc_embeds
