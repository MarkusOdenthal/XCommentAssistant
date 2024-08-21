import logging
import os

from modal import App, Function, Image, Secret

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

image = Image.debian_slim(python_version="3.11").pip_install(
    "langchain",
    "langchain-anthropic",
    "langchain-core",
    "langchain-openai",
    "langchainhub",
)
with image.imports():
    from langchain import hub
    from langchain_anthropic import ChatAnthropic
    from langchain_core.output_parsers import StrOutputParser, XMLOutputParser
    from langchain_openai import ChatOpenAI
    import uuid

app = App(
    "reply_pipeline", image=image, secrets=[Secret.from_name("SocialMediaManager")]
)


@app.function()
def generate_reply(tweet: str, user_name: str, user_description: str):

    def rerank_results(results, similarity_weight=0.7, engagement_weight=0.3):
        max_engagement = max(r['metadata'].get('reply_engagements', 0) for r in results)
        for result in results:
            similarity_score = result['score']  # Assuming this is the similarity score from 0-1
            engagement_count = result['metadata'].get('reply_engagements', 0)  # Assuming this field exists
        
            # Normalize engagement count (you may need to adjust this based on your data)
            normalized_engagement = engagement_count / max_engagement if max_engagement > 0 else 0

            # Calculate combined score
            combined_score = (similarity_score * similarity_weight) + (normalized_engagement * engagement_weight)

            result['combined_score'] = combined_score

        # Sort results by combined score in descending order
        return sorted(results, key=lambda x: x['combined_score'], reverse=True)

    OUR_AUDIENCE = """I help mid-career tech professionals (30-40 years old) leverage smart systems and automation to exponentially grow their X presence, attract high-value clients, and maintain work-life balance."""
    CONTENT_STRATEGY = """I share data-driven insights on X growth hacks, automated engagement strategies, and system optimization techniques specifically for tech professionals building their personal brand on X."""

    try:
        query = Function.lookup("pinecone", "query")
        embed = Function.lookup("openai_client", "embed")
    except Exception as e:
        logger.exception(f"Function lookup failed: {str(e)}")
        return

    # load chains
    xml_parser = XMLOutputParser()

    config = {"metadata": {"conversation_id": str(uuid.uuid4())}}

    gpt_4o_mini = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)

    gpt4o = ChatOpenAI(model="gpt-4o", temperature=1.0)
    sonnet_3_5_0 = ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,
    )
    sonnet_3_5_0_with_fallback = sonnet_3_5_0.with_fallbacks([gpt4o])

    tweet_embed = embed.remote([tweet])[0]
    example_comments = query.remote(
        index_name="x-comments-markus-odenthal", q_vector=tweet_embed, top_k=100
    )
    example_comments_str = "\n".join(
        [
            f"Post: {idx + 1}\n{comment['metadata']['original_post']}\n{'-'*50}\nReply: {idx + 1}\n{comment['metadata']['reply']}\n{'='*50}"
            for idx, comment in enumerate(example_comments[:10])
        ]
    )

    example_posts = query.remote(
        index_name="x-posts-markus-odenthal", q_vector=tweet_embed
    )
    example_posts_str = "\n".join(
        [
            f"Post: {idx + 1}\n{post['metadata']['text']}\n{'-'*50}"
            for idx, post in enumerate(example_posts)
        ]
    )

    ##########################################################
    # Summarize the retrieved post and comments
    ##########################################################  
    content_summary_prompt = hub.pull("content_summary")
    content_summary_chain = (
        content_summary_prompt | gpt_4o_mini | xml_parser
    )
    content_summary = content_summary_chain.invoke(
        {   
            "TOPIC": tweet,
            "OUR_POSTS": example_posts_str,
            "OUR_REPLIES": example_comments_str,
        },
        config=config
    )
    content_summary_str = content_summary["root"][1]["summary"]

    ##########################################################
    # Create the engagement strategy   
    ##########################################################  
    engagement_strategy_prompt = hub.pull("engagement_strategy")
    engagement_strategy_chain = (
        engagement_strategy_prompt | sonnet_3_5_0_with_fallback | xml_parser
    )
    engagement_strategy = engagement_strategy_chain.invoke(
        {
            "OUR_AUDIENCE": OUR_AUDIENCE,
            "CONTENT_STRATEGY": CONTENT_STRATEGY,
            "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
            "PAST_CONTENT_SUMMARY": content_summary_str,
            "INFLUENCER_POST": tweet
        },
        config=config
    )
    engagement_idea = engagement_strategy["root"][1]["reply_outline"]

    ##########################################################
    # Create the reply draft   
    ##########################################################  
    example_comments_reranked = rerank_results(example_comments, similarity_weight=0.3, engagement_weight=0.7)
    example_comments_reranked_str = "\n".join(
        [
            f"Post: {idx + 1}\n{comment['metadata']['original_post']}\n{'-'*50}\nReply: {idx + 1}\n{comment['metadata']['reply']}\n{'='*50}"
            for idx, comment in enumerate(example_comments_reranked[:5])
        ]
    )
    reply_drafter_prompt = hub.pull("reply_drafter")
    reply_drafter_chain = (
        reply_drafter_prompt | sonnet_3_5_0_with_fallback | xml_parser
    )
    reply_draft = reply_drafter_chain.invoke(
        {   
            "INFLUENCER_POST": tweet,
            "REPLY_OUTLINE": engagement_idea,
            "PAST_POST_REPLIES": example_comments_reranked_str,
        },
        config=config
    )
    final_reply = reply_draft["root"][1]["social_media_reply"]

    # TODO: Search: With this reply we search now similar past replies, important is that they are similar
    # TODO: AI: Then we use next AI to refine this reply with this new information
    return final_reply


@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    generate_reply.local(
        tweet="""The cost of ignorance is easy to quantify but hard to comprehend.
The cost of not knowing how to get what you want is the value of the thing you want.
And that education costs time and money.
You pay with the one you value least.""",
        user_name="Alex Hormozi",
        user_description="Day Job: I invest and scale companies at http://Acquisition.com | Co-Owner, Skool. Side Hustle: I show how we do it. Business owners click below ⬇️",
    )
