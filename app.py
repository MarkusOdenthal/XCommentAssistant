import logging
import os

import cohere
import tweepy
from cohere import ClassifyExample
from flask import Flask, request
from langchain import hub
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import XMLOutputParser

from config import ANTI_VISION, BEHAVIORS, COMMENTS, SKILLS, VISION, YOUR_PAST

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

co = cohere.Client(os.getenv("COHERE_API_KEY"))

prompt = hub.pull("x_comment_prompt")
model = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.2,
)
parser = XMLOutputParser()
chain = prompt | model | parser


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
                    text="The. first AI-generated commercial! This one is from Sora. I suspect Toy-r-us made it so it can benefit from the buzz and hype of everyone sharing itThis one has a very uncanny valley vibe, so it's not quite as compelling. The Kling MadMax beer one was much better.",
                    label="uninteresting_topic",
                ),
                ClassifyExample(
                    text="Deepseek Coder v2 Is The New Open-Source King And Beats The Best Gemini Model. Deepseek-coder has officially put OSS in third position, just behind OAI and Anthropic. It excels at coding and reasoning and scores very high on Livebench AI, the ONLY benchmark you can't game!",
                    label="uninteresting_topic",
                ),
                ClassifyExample(
                    text="Several people seem frustrated that they can't use the web or generate images using Sonnet 3.5 You can do this with ChatLLM. Don't tell our engineering team about this post; they will be mad at me! We are running hot...\n\n",
                    label="uninteresting_topic",
                ),
                ClassifyExample(
                    text="There will be two classes of people in the future.\n\nThe LLM savvy and the LLM clueless\n\nThe LLM savvy will understand the strengths of different LLMs, will know how to apply them in their jobs and personal lives, use them prolifically, and experience huge career and productivity gains.\n\nThe LLM clueless class will barely know what is happening, claim AI is dangerous, and slowly become obsolete.\n\nThere will be a great divide between these two classes. Even bigger than the rich and the poor of today",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="Top people set clear goals:\n\n• They outline what they want\n• The write everything down\n• They make detailed plans\n• They track their progress\n\nUnsuccessful people leave it all in their head\n\nAnd let their head talk themselves out of it...",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="LLMs Are Great Levelers!\n\nGoogle search up-skilled millions and helped us level up to the so called experts of yester years.\n\nYou could instantly fact check them in minutes, prove or dis-prove them and go toe to toe!\n\nLLMs take this up a notch and uplevel our skills - from basic English speaking to coding and expert research, LLMs equalize the playing field!\n\nOverall this is a big deal for our entire species. We will no longer have a huge resource constraint on stellar talent as more people move from the above average bracket into the expert bracket and from the beginner bracket to the mid-level overnight!",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="Give information. Monetize personalization.",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="Over the last 6 months, we have seen\n\nAI generated\n\n- audiobooks\n- influencers on instagram\n- commercials\n- songs\n- novels\n- proteins\n- documents\n- reviews, SEO content farms\n- code and agents\n\nThe quality of these generated artifacts is as good, if not better than what humans are able to produce!\n\nThis is just in the last 6 months! Imagine what happens in the next 2 years",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="Content 101:\n\nWhat worked last week, may not work today.\n\nIf your content is not evolving, it’s dying.",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="I failed many times before I could make my first dollar on the internet.\n\nDon't quit while you fail in first attempt:\n\n10 no's = closer to a yes.\n10 flops = closer to a win.\n10 mistakes = closer to mastery.\n\nKeep failing forward.",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="I don't know who needs to hear this.\nBut when you're faced with a decision to make – choose the one that creates change.\nThat's how you grow beyond what you think you're capable of.",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="solopreneurship isn ' t about constantly working on your business. it ' s about building a business that works for you.",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="Both Microsoft and Amazon have been very disappointing and far behind when it comes to foundation models!\nEven Nvidia, a hardware player, dropped a very good OSS model Nemotron, a couple of weeks ago.\nTheir reliance on OAI and Anthropic will cripple them in the long run. FWIW",
                    label="uninteresting_topic",
                ),
                ClassifyExample(
                    text="I know many multi-six-figure creators.\n• One used to be a dentist\n• One used to be a bartender\n• One used to be a music teacher\n• One used to live in a trailer park\nDon't let the start of your story\nDictate who you'll become in the end",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="Fall in love with the problem, not your solution.",
                    label="interesting_topic",
                ),
                ClassifyExample(
                    text="Daily writing straightline your thoughts.\n\nI used to mumble a lot, but now I talk in a logical and structured manner.\n\nThose frameworks are now stuck inside my head.\n\nIt's the ultimate tool to sharpen your thinking.",
                    label="interesting_topic",
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


@app.route("/generate_comment", methods=["POST"])
def generate_comment():
    try:
        data = request.get_json()
        tweet = data.get("tweet")

        if not tweet:
            logger.warning("No tweet provided in the request")
            return {"error": "No tweet provided"}, 400

        comments = chain.invoke(
            {
                "YOUR_PAST": YOUR_PAST,
                "SKILLS": SKILLS,
                "BEHAVIORS": BEHAVIORS,
                "ANTI_VISION": ANTI_VISION,
                "VISION": VISION,
                "COMMENTS": COMMENTS,
                "BIG_ACCOUNT_POST": tweet,
            }
        )

        return {"comments": comments["root"][1]}

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500


def get_tweet_statistics(tweet_url):
    try:
        # Extract tweet ID from URL
        tweet_id = tweet_url.split("/")[-1].split("?")[0]

        # Initialize Twitter API client
        client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
        )
        # Fetch tweet data
        response = client.get_tweets(
            [tweet_id],
            tweet_fields=["public_metrics", "non_public_metrics"],
            user_auth=True,
        )

        if not response.data:
            return {"error": "Tweet not found or inaccessible"}

        metrics = {
            **response.data[0].public_metrics,
            **response.data[0].non_public_metrics,
        }
        return metrics

    except Exception as e:
        logger.error(f"Error fetching tweet statistics: {str(e)}", exc_info=True)
        return {"error": str(e)}


@app.route("/tweet_statistics", methods=["POST"])
def tweet_statistics():
    try:
        data = request.get_json()
        tweet_url = data.get("tweet_url")

        if not tweet_url:
            return {"error": "No tweet URL provided"}, 400

        stats = get_tweet_statistics(tweet_url)
        return stats

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(debug=True)
