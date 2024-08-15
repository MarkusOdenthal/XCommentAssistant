import logging
from flask import Flask
from .routes import init_routes
from config import Config
from .langchain_setup import load_chains

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Load and set up chains
    chains = load_chains()
    app.config['viral_social_media_comments_ideas_chain'] = chains['viral_social_media_comments_ideas_chain']
    app.config['viral_social_media_comments_refine_chain'] = chains['viral_social_media_comments_refine_chain']

    # Initialize routes
    init_routes(app)
    return app
