import logging
from flask import Flask
from flask_apscheduler import APScheduler
from .routes import init_routes
from .jobs import init_jobs
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

    # Initialize and start the scheduler
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    # Initialize jobs
    init_jobs(scheduler)

    return app
