import logging
from flask import Flask
from .routes import init_routes
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Initialize routes
    init_routes(app)
    return app
