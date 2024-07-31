# app/cohere_client.py
import os
import cohere

co = cohere.Client(os.getenv("COHERE_API_KEY"))
