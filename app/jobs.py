from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def init_jobs(scheduler):
    @scheduler.task('interval', id='do_job', seconds=3, misfire_grace_time=900)
    def job():
        print("Scheduled job executed")
        print(f"Time: {datetime.now()}")
        logger.info(f"Scheduled job executed at {datetime.now()}")
