import os

import openai
from pinecone import Pinecone, ServerlessSpec

openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


def create_index(index_name):
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    _ = pc.Index(index_name)
    pass


def embed(docs: list[str]) -> list[list[float]]:
    res = openai.embeddings.create(input=docs, model="text-embedding-3-small")
    doc_embeds = [r.embedding for r in res.data]
    return doc_embeds


def upsert_data(index_name, data):
    doc_embeds = embed([d["text"] for d in data])
    vectors = []
    for d, e in zip(data, doc_embeds):
        vectors.append({"id": d["id"], "values": e, "metadata": d["metadata"]})
    index = pc.Index(index_name)
    index.upsert(vectors=vectors)
    pass

def query_index(index_name, query):
    index = pc.Index(index_name)
    x = embed([query])
    results = index.query(
        vector=x[0],
        top_k=10,
        include_values=False,
        include_metadata=True
    )
    return results