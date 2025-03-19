import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from jarvis.app import mongo_purge_all_memories, mongo_purge_memories, mongo_append_memory, mongo_get_memories
from jarvis.models import User

from pyttman.core.plugins.base import PyttmanPluginIntercept
from pyttman.core.plugins.mongoengine_plugin import MongoEnginePlugin
from pyttman.core.plugins.openai_plugin import OpenAIPlugin

load_dotenv()

DEV_MODE = False

DB_NAME_PROD = os.getenv("MONGO_DB_NAME_PROD")
DB_NAME_DEV = os.getenv("MONGO_DB_NAME_DEV")
APPEND_LOG_FILES = True
USE_TEST_SERVER = os.getenv("USE_TEST_SERVER") == "True"
OFFLINE_MODE = False

ROUTER = {
    # The router is responsible for matching messages to Intents.
    "ROUTER_CLASS": "pyttman.core.middleware.routing.FirstMatchingRouter",

    # A random element is chosen as a reply, if your app can't find a matching Intent
    "COMMAND_UNKNOWN_RESPONSES": [
        "Hmm, nu är jag inte med...",
        "Jag fattar inte. :(",
        "...?",
        "Nä, jag förstår inte vad du menar.",
        "Hmmm.. prova igen, jag hänger inte med?",
        "Blipp, blopp... jag hajar inte vad du menar.",
    ],

    # Pyttman has built-in help for all Intents. If a message contains the
    # following word, the help section for the matching Intent is returned.
    "HELP_KEYWORD": "hjälp",

    # Should an exception occur in your app, the following reply is returned
    # to the end user.
    "FATAL_EXCEPTION_AUTO_REPLY": "Åh nej! Något gick fel. "
                                  "Försök igen om en liten stund."
}

# Plugins can be installed using pip, and they can offer various
# functionalities - such as providing an API for setting 'message.author'
# as a matching user in a custom database, language translations and
# much more.
stockholm_time = datetime.now(tz=ZoneInfo("Europe/Stockholm")
                              ).strftime("%m/%d/%Y - %H:%M:%S")

PLUGINS = [
    MongoEnginePlugin(
        db_name=os.getenv("MONGO_DB_NAME_DEV") if DEV_MODE else os.getenv("MONGO_DB_NAME_PROD"),
        host=os.getenv("MONGO_DB_URL"),
        port=os.getenv("MONGO_DB_PORT"),
        username=os.getenv("MONGO_DB_USER"),
        password=os.getenv("MONGO_DB_PASSWORD"),
        user_binding=MongoEnginePlugin.MessageUserBinding(
            user_model_class=User,
            custom_queryset_method_name="from_alias",
        ),
        allowed_intercepts=[
            PyttmanPluginIntercept.before_app_start,
            PyttmanPluginIntercept.after_app_stops,
            PyttmanPluginIntercept.before_intent
        ]
    ),
    OpenAIPlugin(
        api_key=os.environ["OPENAI_API_KEY"],
        system_prompt=stockholm_time + os.environ["OPENAI_SYSTEM_PROMPT"],
        model="gpt-4o-mini",
        max_tokens=580,
        enable_conversations=True,
        enable_memories=True,
        purge_all_memories_callback=mongo_purge_all_memories,
        purge_memories_callback=mongo_purge_memories,
        add_memory_callback=mongo_append_memory,
        get_memories_callback=mongo_get_memories,
        allowed_intercepts=[
            PyttmanPluginIntercept.no_intent_match,
        ]
    ),
    OpenAIPlugin(
        api_key=os.environ["OPENAI_API_KEY"],
        system_prompt=os.environ["OPENAI_SPELL_CHECKER_SYSTEM_PROMPT"],
        model="gpt-4o-mini",
        max_tokens=580,
        allowed_intercepts=[
            PyttmanPluginIntercept.before_router
        ]
    )
]

ABILITIES = [
    "jarvis.abilities.finance.ability.FinanceAbility",
    "jarvis.abilities.administrative.ability.AdministrativeAbility",
    "jarvis.abilities.timekeeper.ability.TimeKeeper",
    "jarvis.abilities.weightkeeper.ability.WeightKeeper",
    "jarvis.abilities.recipes.ability.RecipesAbility",
]

if os.getenv("USE_STT_CLIENT") == "True":
    CLIENT = {
        "class": "jarvis.clients.speech.speech_client.SpeechClient",
    }
else:
    CLIENT = {
        "class": "pyttman.clients.community.discord.client.DiscordClient",
        "token": os.getenv("DISCORD_TOKEN_DEV") if USE_TEST_SERVER else os.getenv("DISCORD_TOKEN_PROD"),
        "guild": os.getenv("DISCORD_GUILD_DEV") if USE_TEST_SERVER else os.getenv("DISCORD_GUILD_PROD"),
        "discord_intent_flags": {
            "message_content": True,
            "dm_messages": True,
            "guild_messages": True,
            "messages": True
        }
    }

APP_BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

LOG_FILE_DIR = APP_BASE_DIR / Path("logs")

LOG_TO_STDOUT = True

APP_NAME = "jarvis"
APP_VERSION = "1.5.5"
DATETIME_FORMAT = "%Y-%m-%d-%H:%M"
TIMESTAMP_FORMAT = "%H:%M"

TIME_ZONE = datetime.utcnow().astimezone().tzinfo
STATIC_FILES_DIR = APP_BASE_DIR / "static"