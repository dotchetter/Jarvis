import mongoengine
from pyttman import app


@app.hooks.run("before_start")
def setup():

    # Connect to the appropriate MongoDB Atlas database
    if app.settings.DEV_MODE:
        app.settings.DATABASE["db"] = app.settings.DB_NAME_DEV
    else:
        app.settings.DATABASE["db"] = app.settings.DB_NAME_PROD
    mongoengine.connect(**app.settings.DATABASE)
