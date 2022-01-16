import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import certifi

load_dotenv()

DEV_MODE = False

INTERACTIVE_SHELL = False

# Selection is performed in
DB_NAME_PROD = os.getenv("MONGO_DB_NAME_PROD")
DB_NAME_DEV = os.getenv("MONGO_DB_NAME_DEV")

db_name = DB_NAME_DEV if DEV_MODE else DB_NAME_PROD

MONGO_DB_CONFIG = {
    "tlsCAFile": certifi.where(),
    "db": None,  # Configured in Ability 'Configure' hook
    "host": os.getenv("MONGO_DB_URL"),
    "username": os.getenv("MONGO_DB_USER"),
    "password": os.getenv("MONGO_DB_PASSWORD"),
    "port": int(os.getenv("MONGO_DB_PORT"))
}

# Create a new log file for each time your app starts, or append the most recent one.
APPEND_LOG_FILES = True

# Configure the behavior of the MessageRouter here
MESSAGE_ROUTER = {

    # The MessageRouter routes messages to your app's Intent classes.
    # To see the available classes and choose on that fits your app,
    # check out the documentation on GitHub.
    "ROUTER_CLASS": "pyttman.core.parsing.routing.FirstMatchingRouter",

    # Define a collection of strings to return to the user if no command matched
    # the user's message. One is randomly chosen by the Router and returned to
    # the user.
    "COMMAND_UNKNOWN_RESPONSES": [
        "Ursäkta, jag förstår inte?",
    ],

    # Define the keyword for Pyttman's auto-generated help pages to be
    # displayed for a user, if they type this word in the beginning of
    # a message. The keyword is case insensitive and has to occur as
    # first string in the message from the user.
    "HELP_KEYWORD": "hjälp",
}

ABILITIES = [
    "jarvis.abilities.finances.ability.FinanceAbility",
    "jarvis.abilities.administrative.ability.AdministrativeAbility"
]

FATAL_EXCEPTION_AUTO_REPLY = "Åh nej! Något gick fel... Simon, kikar du på detta:"


CLIENT = {
    "class": "pyttman.clients.community.discord.client.DiscordClient",
    "token": os.getenv("DISCORD_TOKEN_DEV") if DEV_MODE else os.getenv("DISCORD_TOKEN_PROD"),
    "guild": os.getenv("DISCORD_GUILD_DEV") if DEV_MODE else os.getenv("DISCORD_GUILD_PROD"),
}

# No need to change this setting
APP_BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

# No need to change this setting
LOG_FILE_DIR = APP_BASE_DIR / Path("logs")

# This setting is set by pyttman-cli when you create your project.
# Do not change it afterwards without also renaming the directory for your app.
APP_NAME = "jarvis"

TIME_ZONE = datetime.utcnow().astimezone().tzinfo
