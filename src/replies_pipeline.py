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

app = App(
    "reply_pipeline", image=image, secrets=[Secret.from_name("SocialMediaManager")]
)


@app.function()
def generate_reply(tweet: str, user_name: str, user_description: str):
    AUDIENCE = """Time-constrained solopreneurs and founders with valuable expertise who want to rapidly increase engagement and attract high-quality customers on X through a premium, personalized AI-assisted ghostwriting service for strategic real-time replies."""

    PERSONAL_INFORMATION = """Name: Markus Odenthal
Twitter Bio: Posts on staying valuable in the AI era. How to use AI to share your human expertise on X. + sharing my insights on my journey to becoming the REPLY GUY.
Current Follower Count: 800
Some more information about me: Currently I'm working as a Machine Learning Engineer in my 9-5. I love my Job and I'm passionate about how AI can help us to archive more. I also really like helping other people and connect and learn from them. I'm a big fan of the "build in public" movement and I'm trying to help other people to get more visibility on X by giving them tips and tricks on how to engage with their audience. Special the replying to comments is a big part of my strategy and I'm always looking for new ways to improve my replies. For this I'm looking for ways to use AI to improve this replies but still keep them human. We need a good combination of human and AI."""

    COPYWRITING_STYLE = """When generating the reply, follow these guidelines:

1. Avoid jargon, buzzwords, sales-y language, long sentences, flowery language (like: Spot on, game-changer), metaphors, analogies, clichés, and overused phrases.
2. Use short, simple sentences for easier reading. Mix in some one or two-word sentences for impact, but vary sentence length to maintain interest.
3. Start some sentences with transition words like "and," "but," "so," and "because" to improve flow and readability, even if it's not always grammatically correct.
4. Write at an 8th-grade reading level, using clear, straightforward, and conversational language.
5. Keep the tone engaging and add a touch of humor where appropriate.
6. Prioritize clarity and readability over strict grammatical rules when it enhances the overall message and keeps readers engaged.
7. Try to write you instead of me. This will make the reader feel more involved.
Remember, the goal is to create a reply that's easy to understand, engaging to read, and effectively communicates the intended message."""

    try:
        query = Function.lookup("pinecone", "query")
        embed = Function.lookup("openai_client", "embed")
    except Exception as e:
        logger.exception(f"Function lookup failed: {str(e)}")
        return

    # load chains
    xml_parser = XMLOutputParser()
    str_parser = StrOutputParser()

    gpt_4o_mini = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)

    social_media_agent_information_summary_prompt = hub.pull(
        "social_media_agent_information_summary"
    )
    social_media_agent_information_summary_chain = (
        social_media_agent_information_summary_prompt | gpt_4o_mini | xml_parser
    )

    viral_social_media_comments_ideas_prompt = hub.pull(
        "viral_social_media_comments_ideas"
    )
    viral_social_media_comments_ideas_chain = (
        viral_social_media_comments_ideas_prompt | gpt_4o_mini | str_parser
    )

    gpt4o = ChatOpenAI(model="gpt-4o", temperature=1.0)
    sonnet_3_5_0 = ChatAnthropic(
        model="claude-3-5-sonnet-20240620",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,
    )
    sonnet_3_5_0_with_fallback = sonnet_3_5_0.with_fallbacks([gpt4o])

    viral_social_media_comments_refine_prompt = hub.pull(
        "viral_social_media_comments_refine"
    )
    viral_social_media_comments_refine_chain = (
        viral_social_media_comments_refine_prompt
        | sonnet_3_5_0_with_fallback
        | xml_parser
    )

    tweet_embed = embed.remote([tweet])[0]
    example_comments = query.remote(
        index_name="x-comments-markus-odenthal", q_vector=tweet_embed
    )
    example_comments_str = "\n".join(
        [
            f"Post: {idx + 1}\n{comment['metadata']['original_post']}\n{'-'*50}\nReply: {idx + 1}\n{comment['metadata']['reply']}\n{'='*50}"
            for idx, comment in enumerate(example_comments)
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
    summary = social_media_agent_information_summary_chain.invoke(
        {
            "POST_TO_REPLY": tweet,
            "OUR_PREVIOUS_POSTS": example_posts_str,
            "OUR_PAST_REPLIES_AND_POSTS": example_comments_str,
        }
    )
    post_analysis = summary["root"][0]["analysis"]
    relevant_previous_post_info = summary["root"][1]["relevant_previous_post_info"]
    useful_past_reply_info = summary["root"][2]["useful_past_reply_info"]

    ideas = viral_social_media_comments_ideas_chain.invoke(
        {
            "AUDIENCE_INFO": AUDIENCE,
            "PERSONAL_INFORMATION": PERSONAL_INFORMATION,
            "PREVIOUS_POSTS": relevant_previous_post_info,
            "EXAMPLE_COMMENTS": useful_past_reply_info,
            "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
            "POST_TO_COMMENT_ON": tweet,
            "POST_ANALYSIS": post_analysis,
            "COPYWRITING": COPYWRITING_STYLE,
        }
    )

    final_comment = viral_social_media_comments_refine_chain.invoke(
        {
            "AUDIENCE_INFO": AUDIENCE,
            "PERSONAL_INFORMATION": PERSONAL_INFORMATION,
            "EXAMPLE_COMMENTS": useful_past_reply_info,
            "PREVIOUS_POSTS": relevant_previous_post_info,
            "INFLUENCER_BIO": f"Name: {user_name}\nBio: {user_description}",
            "POST_TO_REPLY": tweet,
            "COPYWRITING_STYLE": COPYWRITING_STYLE,
            "REPLY_IDEAS": ideas,
        }
    )
    final_reply = final_comment["root"][1]["final_reply"]
    return final_reply, example_comments[0]


@app.local_entrypoint()
def test_function():
    logger.info("Starting test function")
    generate_reply.local(
        tweet="Most businesses fail, not due to lack of effort, but lack of systems.",
        user_name="MATT GRAY",
        user_description="The Systems Guy” | Proven systems to grow a profitable audience with organic content. Founder & CEO @founderos",
    )
