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

APPEND_LOG_FILES = True

MESSAGE_ROUTER = {

    "ROUTER_CLASS": "pyttman.core.parsing.routing.FirstMatchingRouter",

    "COMMAND_UNKNOWN_RESPONSES": [
        "Ursäkta, jag förstår inte?",
    ],
    "HELP_KEYWORD": "hjälp",
}

ABILITIES = [
    "jarvis.abilities.finance.ability.FinanceAbility",
    "jarvis.abilities.administrative.ability.AdministrativeAbility"
]

FATAL_EXCEPTION_AUTO_REPLY = "Åh nej! Något gick fel. Försök igen om en " \
                             "liten stund."


CLIENT = {
    "class": "pyttman.clients.community.discord.client.DiscordClient",
    "token": os.getenv("DISCORD_TOKEN_DEV") if DEV_MODE else os.getenv("DISCORD_TOKEN_PROD"),
    "guild": os.getenv("DISCORD_GUILD_DEV") if DEV_MODE else os.getenv("DISCORD_GUILD_PROD"),
}

APP_BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

LOG_FILE_DIR = APP_BASE_DIR / Path("logs")

LOG_TO_STDOUT = True
APP_NAME = "jarvis"
APP_VERSION = "1.0.7"
TIME_ZONE = datetime.utcnow().astimezone().tzinfo
