import os

import modal

image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "pinecone-client"
)
with image.imports():
    import logging
    import os

    from pinecone import Pinecone, ServerlessSpec

app = modal.App(
    "pinecone", image=image, secrets=[modal.Secret.from_name("SocialMediaManager")]
)


@app.cls()
class PineconeClient:
    @modal.enter()
    def connect(self):
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        if pinecone_api_key is None:
            raise ValueError("PINECONE_API_KEY is not set")
        self.pc = Pinecone(api_key=pinecone_api_key)
        return self.pc

    @modal.method()
    def create_index(self, index_name: str):
        pc = self.pc
        logging.info("Connecting to Pinecone")

        try:
            if index_name not in pc.list_indexes().names():
                pc.create_index(
                    name=index_name,
                    dimension=1536,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
            _ = pc.Index(index_name)
        except Exception as e:
            logging.error(f"Failed to create index {index_name}: {e}")
            raise
        pass

    @modal.method()
    def upsert_data(self, index_name: str, vectors: list[dict]):
        pc = self.pc
        index = pc.Index(index_name)
        index.upsert(vectors=vectors)
        pass

    @modal.method()
    def query_index(self, index_name: str, query_vector, top_k=10):
        """
        Query the Pinecone index with a given query and return the results.

        Parameters:
            index_name (str): The name of the Pinecone index.
            query (str): The query to search for in the index.
            top_k (int, optional): The number of top results to return. Default is 10.

        Returns:
            dict: The query results.
        """
        pc = self.pc
        index = pc.Index(index_name)
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_values=False,
            include_metadata=True,
        )
        matches = [
            {"id": match.id, "score": match.score, "metadata": match.metadata}
            for match in results.matches
        ]
        return matches

@app.function()
def query(data: dict) -> list[dict]:
    """Query the Pinecone index with a given query and return the results.
    """
    index_name = data["index_name"]
    q_vector = data["q_vector"]
    return PineconeClient().query_index.remote(index_name, q_vector)

@app.function()
def upsert(index_name: str, vectors: list[dict]):
    """Upsert data into a Pinecone index.

    Parameters:
        vectors (list[dict]): The vectors to upsert into the index.
    """
    PineconeClient().upsert_data.remote(index_name, vectors)


@app.local_entrypoint()
def main(query: str):
    """Creates the collection if it doesn't exist, wiping it first if requested.

    Note that this script can only be run if the `WCS_ADMIN_KEY` is set in the `wiki-weaviate` secret.

    Run this function with `modal run database.py`."""
    index_name = "..."
    PineconeClient().create_index.remote(index_name)
