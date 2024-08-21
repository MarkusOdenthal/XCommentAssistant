import logging
import math
import os
from datetime import datetime, timezone
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
    from langchain_core.output_parsers import XMLOutputParser
    from langchain_openai import ChatOpenAI
    import uuid

app = App(
    "reply_pipeline", image=image, secrets=[Secret.from_name("SocialMediaManager")]
)


@app.function()
def generate_reply(tweet: str, user_name: str, user_description: str):

    def rerank_results(results, similarity_weight=0.7, engagement_weight=0.3, half_life_days=30):
        current_time = datetime.now(timezone.utc)
        max_engagement = max(r['metadata'].get('reply_engagements', 0) for r in results)

        for result in results:
            similarity_score = result['score']  # Assuming this is the similarity score from 0-1
            engagement_count = result['metadata'].get('reply_engagements', 0)  # Assuming this field exists
            timestamp = datetime.fromisoformat(result['metadata'].get('reply_created_at', '2024-01-01T00:00:00+00:00'))

            # Normalize engagement count (you may need to adjust this based on your data)
            normalized_engagement = engagement_count / max_engagement if max_engagement > 0 else 0

            # Calculate time decay
            age_days = (current_time - timestamp).days
            time_decay = math.pow(0.5, age_days / half_life_days)

            # Calculate combined score
            combined_score = (
                similarity_score * similarity_weight +
                normalized_engagement * engagement_weight
            ) * time_decay

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
            "INFLUENCER_POST": tweet,
            "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
            "OUR_AUDIENCE": OUR_AUDIENCE,
            "CONTENT_STRATEGY": CONTENT_STRATEGY,
            "PAST_CONTENT_SUMMARY": content_summary_str,  
        },
        config=config
    )
    final_reply = engagement_strategy["root"][1]["reply_ideas"]

    def get_average_expert_confidence_score(comment: str):
        comment_embed = embed.remote([comment])[0]
        comments = query.remote(
            index_name="x-only-comments-markus-odenthal", q_vector=comment_embed, top_k=30
        )
        comments_reranked = rerank_results(comments, similarity_weight=0.3, engagement_weight=0.7)
        comments_reranked = comments_reranked[:5]
        average_expert_confidence_score = sum([comment['combined_score'] for comment in comments_reranked]) / len(comments_reranked)
        
        # Get the top 3 performing comments
        top_3_comments = [
            {
                'text': comment['metadata']['reply'],
                'score': comment['combined_score'],
                'engagement_rate': comment['metadata'].get('reply_engagements', 0),
                'original_post': comment['metadata']['original_post']
            }
            for comment in comments_reranked[:3]
        ]
        
        return round(average_expert_confidence_score, 2), top_3_comments
    
    # Add average expert confidence score and top 3 comments to each reply idea
    for idea in final_reply:
        reply_text = list(idea.values())[0]
        confidence_score, top_comments = get_average_expert_confidence_score(reply_text)
        idea['confidence_score'] = confidence_score
        idea['top_comments'] = top_comments
    
    # Sort ideas by confidence score in descending order
    final_reply.sort(key=lambda x: x['confidence_score'], reverse=True)
    
    # Create the final reply string with scores at the beginning of each idea
    ideas_str = "\n---\n".join([f"{idea['confidence_score']}: {list(idea.values())[0]}" for idea in final_reply[:3]])

    best_idea = final_reply[0]
    best_idea_str = list(best_idea.values())[0]
    top_comments = best_idea['top_comments']
    top_comments_str = "\n".join([f"Post: {idx + 1}\n{comment['original_post']}\n{'-'*10}\nReply: {idx + 1}\n{comment['text']}\n{'-'*10}\n{int(comment['engagement_rate'])} engagements\n{'='*50}" for idx, comment in enumerate(top_comments)])
    reply_refinement_prompt = hub.pull("reply_refinement")
    reply_refinement_chain = (
        reply_refinement_prompt | sonnet_3_5_0_with_fallback | xml_parser
    )
    reply_refinement = reply_refinement_chain.invoke(
        {   
            "ORIGINAL_POST": tweet,
            "REPLY_DRAFT": ideas_str,
            "EXAMPLE_REPLIES": top_comments_str,
        },
        config=config
    )
    final_reply_str = reply_refinement["root"][1]["refined_reply"]
    ##########################################################
    # Create the reply draft   
    ##########################################################  
    # example_comments_reranked = rerank_results(example_comments, similarity_weight=0.3, engagement_weight=0.7)
    # example_comments_reranked_str = "\n".join(
    #     [
    #         f"Post: {idx + 1}\n{comment['metadata']['original_post']}\n{'-'*50}\nReply: {idx + 1}\n{comment['metadata']['reply']}\n{'='*50}"
    #         for idx, comment in enumerate(example_comments_reranked[:5])
    #     ]
    # )
    # reply_drafter_prompt = hub.pull("reply_drafter")
    # reply_drafter_chain = (
    #     reply_drafter_prompt | sonnet_3_5_0_with_fallback | xml_parser
    # )
    # reply_draft = reply_drafter_chain.invoke(
    #     {   
    #         "INFLUENCER_POST": tweet,
    #         "REPLY_OUTLINE": engagement_idea,
    #         "PAST_POST_REPLIES": example_comments_reranked_str,
    #     },
    #     config=config
    # )
    # final_reply = reply_draft["root"][1]["social_media_reply"]

    # TODO: Search: With this reply we search now similar past replies, important is that they are similar
    # TODO: AI: Then we use next AI to refine this reply with this new information
    return ideas_str, top_comments_str, final_reply_str


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