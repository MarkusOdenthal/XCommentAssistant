import os

from langchain import hub
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser, XMLOutputParser
from langchain_openai import ChatOpenAI


def load_chains():
    xml_parser = XMLOutputParser()
    str_parser = StrOutputParser()

    gpt_4o_mini = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)
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
        viral_social_media_comments_refine_prompt | sonnet_3_5_0_with_fallback | xml_parser
    )

    return {
        "viral_social_media_comments_ideas_chain": viral_social_media_comments_ideas_chain,
        "viral_social_media_comments_refine_chain": viral_social_media_comments_refine_chain,
    }
