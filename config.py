import os

class Config:
    SCHEDULER_API_ENABLED = True
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
    X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
    X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
    X_ACCESS_CONSUMER_KEY = os.getenv("X_ACCESS_CONSUMER_KEY")
    X_ACCESS_CONSUMER_SECRET = os.getenv("X_ACCESS_CONSUMER_SECRET")
    AUDIENCE = """Time-constrained solopreneurs and founders with valuable expertise who want to rapidly increase engagement and attract high-quality customers on X through a premium, personalized AI-assisted ghostwriting service for strategic real-time replies."""

    PERSONAL_INFORMATION = """Name: Markus Odenthal
Twitter Bio: Posts on staying valuable in the AI era. How to use AI to share your human expertise on X. + sharing my insights on my journey to becoming the REPLY GUY.
Current Follower Count: 800
Some more information about me: Currently I'm working as a Machine Learning Engineer in my 9-5. I love my Job and I'm passionate about how AI can help us to archive more. I also really like helping other people and connect and learn from them. I'm a big fan of the "build in public" movement and I'm trying to help other people to get more visibility on X by giving them tips and tricks on how to engage with their audience. Special the replying to comments is a big part of my strategy and I'm always looking for new ways to improve my replies. For this I'm looking for ways to use AI to improve this replies but still keep them human. We need a good combination of human and AI."""

    COPYWRITING_STYLE = """When generating the reply, follow these guidelines:

1. Avoid jargon, buzzwords, sales-y language, long sentences, flowery language (like: "Spot on, ..."), metaphors, analogies, clichés, and overused phrases.
2. Use short, simple sentences for easier reading. Mix in some one or two-word sentences for impact, but vary sentence length to maintain interest.
3. Start some sentences with transition words like "and," "but," "so," and "because" to improve flow and readability, even if it's not always grammatically correct.
4. Write at an 8th-grade reading level, using clear, straightforward, and conversational language.
5. Keep the tone engaging and add a touch of humor where appropriate.
6. Prioritize clarity and readability over strict grammatical rules when it enhances the overall message and keeps readers engaged.

Remember, the goal is to create a reply that's easy to understand, engaging to read, and effectively communicates the intended message."""
