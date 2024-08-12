import json
import logging
import pathlib
from typing import Any, Dict

from modal import App, Volume

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = App("datastore")

instance = Volume.from_name("instance")
VOL_MOUNT_PATH = pathlib.Path("/instance")


@app.function(volumes={VOL_MOUNT_PATH: instance})
def save_data(data: Dict[str, Any]):
    # TODO: When I get client I need to make sure that this will check first for update in storage.
    store_path = str(VOL_MOUNT_PATH / "data.json")
    logger.info(f"Starting save_data function. Writing data to {store_path}")

    try:
        with open(store_path, "w") as file:
            json.dump(data, file)
        try:
            instance.commit()
        except Exception as e:
            logger.exception(f"Error during instance commit: {str(e)}")
            return
        logger.info(f"Successfully wrote data to {store_path}")
    except (IOError, OSError) as e:
        logger.exception(f"IOError/OSError while writing {store_path}: {str(e)}")
        return


@app.function(volumes={VOL_MOUNT_PATH: instance})
def read_data() -> Dict[str, Any]:
    store_path = str(VOL_MOUNT_PATH / "data.json")
    logger.info(f"Starting read_data function. Reading data from {store_path}")

    try:
        with open(store_path, "r") as file:
            data: Dict[str, Any] = json.load(file)
        logger.info(f"Successfully loaded data from {store_path}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {store_path}")
        return {"users": {}, "max_post_id": 0}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {store_path}")
        return {"users": {}, "max_post_id": 0}
    except PermissionError:
        logger.error(f"Permission denied: {store_path}")
        return {"users": {}, "max_post_id": 0}
    except Exception as e:
        logger.exception(f"Unexpected error reading {store_path}: {str(e)}")
        return {}
