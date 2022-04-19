import os

import certifi
import mongoengine
from pyttman import app
from dotenv import load_dotenv


@app.hooks.run("before_start")
def setup():

    load_dotenv()
    # Connect to the appropriate MongoDB Atlas database
    mongo_db_config = {
        "tlsCAFile": certifi.where(),
        "db": None,  # Configured in Ability 'Configure' hook
        "host": os.getenv("MONGO_DB_URL"),
        "username": os.getenv("MONGO_DB_USER"),
        "password": os.getenv("MONGO_DB_PASSWORD"),
        "port": int(os.getenv("MONGO_DB_PORT"))
    }

    if app.settings.DEV_MODE:
        mongo_db_config["db"] = app.settings.DB_NAME_DEV
    else:
        mongo_db_config["db"] = app.settings.DB_NAME_PROD

    mongoengine.connect(**mongo_db_config)

