import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SCHEDULER_API_ENABLED = True
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
    X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
    X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
    X_ACCESS_CONSUMER_KEY = os.getenv("X_ACCESS_CONSUMER_KEY")
    X_ACCESS_CONSUMER_SECRET = os.getenv("X_ACCESS_CONSUMER_SECRET")
    AUDIENCE = """Bootstrap SaaS founders who want to increase their product's visibility and user acquisition specifically through strategic engagement on X (formerly Twitter) by leveraging "build in public" content and targeted commenting under influential accounts in their niche."""

    PERSONAL_INFORMATION = """Name: Markus Odenthal
Twitter Bio: I help bootstrap SaaS founders 10x visibility on X | Strategic commenting expert | 7Y+ in AI + Software Dev | Dad | Calisthenics practitioner.
Current Follower Count: 800
Some more information about me: I'm not a SaaS Founder but SaaS special Bootstrap SaaS companies are an Topic that really interested me. My Service is to help them to grow on X via commenting on Bigger Accounts."""

    COPYWRITING_STYLE = """When generating the reply, follow these guidelines:

1. Avoid jargon, buzzwords, sales-y language, long sentences, flowery language (like: "Spot on, ..."), metaphors, analogies, clichés, and overused phrases.
2. Use short, simple sentences for easier reading. Mix in some one or two-word sentences for impact, but vary sentence length to maintain interest.
3. Start some sentences with transition words like "and," "but," "so," and "because" to improve flow and readability, even if it's not always grammatically correct.
4. Write at an 8th-grade reading level, using clear, straightforward, and conversational language.
5. Keep the tone engaging and add a touch of humor where appropriate.
6. Prioritize clarity and readability over strict grammatical rules when it enhances the overall message and keeps readers engaged.

Remember, the goal is to create a reply that's easy to understand, engaging to read, and effectively communicates the intended message."""
