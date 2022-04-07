import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEV_MODE = True

INTERACTIVE_SHELL = False

# Selection is performed in
DB_NAME_PROD = os.getenv("MONGO_DB_NAME_PROD")
DB_NAME_DEV = os.getenv("MONGO_DB_NAME_DEV")

db_name = DB_NAME_DEV if DEV_MODE else DB_NAME_PROD

APPEND_LOG_FILES = True

MIDDLEWARE = {

    "ROUTER_CLASS": "pyttman.core.middleware.routing.FirstMatchingRouter",

    "COMMAND_UNKNOWN_RESPONSES": [
        "Ursäkta, jag förstår inte?",
    ],
    "HELP_KEYWORD": "hjälp",

    "FATAL_EXCEPTION_AUTO_REPLY": "Åh nej! Något gick fel. "
                                  "Försök igen om en liten stund."
}

ABILITIES = [
    "jarvis.abilities.finance.ability.FinanceAbility",
    "jarvis.abilities.administrative.ability.AdministrativeAbility"
]


CLIENT = {
    "class": "pyttman.clients.community.discord.client.DiscordClient",
    "token": os.getenv("DISCORD_TOKEN_DEV") if DEV_MODE else os.getenv("DISCORD_TOKEN_PROD"),
    "guild": os.getenv("DISCORD_GUILD_DEV") if DEV_MODE else os.getenv("DISCORD_GUILD_PROD"),
}

APP_BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

LOG_FILE_DIR = APP_BASE_DIR / Path("logs")

LOG_TO_STDOUT = True
APP_NAME = "jarvis"
APP_VERSION = "1.0.9.2"
TIME_ZONE = datetime.utcnow().astimezone().tzinfo
