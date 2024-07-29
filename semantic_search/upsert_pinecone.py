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

if __name__ == "__main__":
    data = [
        {
            "id": "vec1",
            "text": "Apple is a popular fruit known for its sweetness and crisp texture.",
        },
        {
            "id": "vec2",
            "text": "The tech company Apple is known for its innovative products like the iPhone.",
        },
        {"id": "vec3", "text": "Many people enjoy eating apples as a healthy snack."},
        {
            "id": "vec4",
            "text": "Apple Inc. has revolutionized the tech industry with its sleek designs and user-friendly interfaces.",
        },
        {
            "id": "vec5",
            "text": "An apple a day keeps the doctor away, as the saying goes.",
        },
    ]
    upsert_data("x-comments-markus-odenthal", data)
