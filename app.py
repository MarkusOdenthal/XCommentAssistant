import os
import logging

import cohere
from flask import Flask, request
from cohere import ClassifyExample

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

co = cohere.Client(os.getenv("COHERE_API_KEY"))

@app.route("/interesting_topic_classification", methods=["POST"])
def interesting_topic_classifier():
    try:
        logger.info("Received request for topic classification")
        
        # Get the tweet from the incoming JSON request
        data = request.get_json()
        tweet = data.get("tweet")

        if not tweet:
            logger.warning("No tweet provided in the request")
            return {"error": "No tweet provided"}, 400

        logger.info(f"Classifying tweet: {tweet[:50]}...")

        response = co.classify(
            model="embed-english-v3.0",
            inputs=[tweet],
            examples=[
                ClassifyExample(
                    text="Believe it or not - There is an open-source model that beats the latest Gemini model... very handily in both reasoning and code. We will be releasing more details on the state of open-source soon!!",
                    label="uninteresting_topic",
                ),
                ClassifyExample(
                    text="Your niche is created, not found\n\nWhen you:\n\n• Find an obsession\n• Learn as much as you can\n• Share everything you're learning\n• And help as many people as possible\n\nYou'll build a life that never needs a resume ever again",
                    label="interesting_topic",
                ),
            ],
        )
        
        logger.info(f"Classification result: {response.classifications[0].prediction}")
        logger.debug(f"Confidence levels: {response.classifications}")

        return {"classification": response.classifications[0].prediction}

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(debug=True)