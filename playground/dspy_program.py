import dspy
from typing import List, Union, Optional
import os
from modal import Function


class DSPythonicRMClient(dspy.Retrieve):
    def __init__(self, k:int = 3):
        super().__init__(k=k)
        self.query = Function.lookup("pinecone", "query")
        self.embed = Function.lookup("openai_client", "embed")

    def forward(self, query: str, index_name: str, k:Optional[str]) -> dspy.Prediction:
        k = k if k else self.k
        q_vector = self.embed.remote([query])[0]
        response = self.query.remote(index_name=index_name, q_vector=q_vector)
        return dspy.Prediction(
            passages=response
        )

retriever_model = DSPythonicRMClient(
    k=5
)
results = retriever_model(index_name="x-comments-markus-odenthal", query="Explore the significance of quantum computing", k=5)


for result in results:
    print("Document:", result.long_text, "\n")
# How to use
'''
import dspy

lm = ...
url = "http://0.0.0.0"
port = 3000

# pythonic_rm = PythonicRMClient(url=url, port=port)
dspythonic_rm = DSPythonicRMClient(k=3)

dspy.settings.configure(lm=lm, rm=dspythonic_rm)


class DSPyPipeline(dspy.Module):
    def __init__(self):
        super().__init__()
        self.rm = dspy.Retrieve(k=3)

    def forward(self, *args):
        passages = self.rm(query, index_name)'''