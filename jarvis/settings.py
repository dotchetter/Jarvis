import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pyttman_base_plugin import PyttmanPlugin
from pyttman_mongoengine_plugin import MongoEnginePlugin
from pyttman_openai_plugin import OpenAIPlugin

from jarvis.app import mongo_purge_all_memories, mongo_purge_memories, mongo_append_memory, mongo_get_memories
from jarvis.models import User

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
            MongoEnginePlugin.PluginInterceptPoint.before_app_start,
            MongoEnginePlugin.PluginInterceptPoint.after_app_stops,
            MongoEnginePlugin.PluginInterceptPoint.before_intent
        ]
    ),
    OpenAIPlugin(
        api_key=os.environ["OPENAI_API_KEY"],
        system_prompt=os.environ["OPENAI_SYSTEM_PROMPT"],
        model=os.environ["OPENAI_MODEL_ID"],
        time_aware=True,
        memory_updated_notice="Det ska jag komma ihåg.",
        time_zone=ZoneInfo("Europe/Stockholm"),
        enable_conversations=True,
        enable_memories=True,
        purge_all_memories_callback=mongo_purge_all_memories,
        purge_memories_callback=mongo_purge_memories,
        add_memory_callback=mongo_append_memory,
        get_memories_callback=mongo_get_memories,
        allowed_intercepts=[
            PyttmanPlugin.PluginInterceptPoint.no_intent_match,
        ],
    ),
]

ABILITIES = [
    "jarvis.abilities.finance.ability.FinanceAbility",
    "jarvis.abilities.administrative.ability.AdministrativeAbility",
    "jarvis.abilities.timekeeper.ability.TimeKeeper",
    "jarvis.abilities.weightkeeper.ability.WeightKeeper",
    "jarvis.abilities.recipes.ability.RecipesAbility",
    "jarvis.abilities.musicplayer.ability.SpotifyAbility",
]

if os.getenv("USE_STT_CLIENT") == "True":
    CLIENT = {
        "class": "jarvis.clients.speech.speech_client.SpeechClient",
        "greeting_message": os.environ["STT_GREETING_MESSAGE"],
        "silence_seconds_before_standby": os.environ["STT_SILENCE_SECONDS_BEFORE_STANDBY"],
        "standby_mode_message": os.environ["STT_STANDBY_MODE_MESSAGE"],
        "name_similarity_threshold_percent": int(os.environ["STT_NAME_SIMILARITY_THRESHOLD_PERCENT"]),
        "silence_seconds_before_processing": os.environ["STT_SILENCE_SECONDS_BEFORE_PROCESSING"],
        "mute_word": os.environ["STT_MUTE_WORD"],
        "volume_threshold": os.environ["STT_VOLUME_THRESHOLD"],
        "user_name_prompt": os.environ["STT_USER_NAME_PROMPT"],
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
    PLUGINS.append(
        OpenAIPlugin(
            api_key=os.environ["OPENAI_API_KEY"],
            system_prompt=os.environ["OPENAI_SPELL_CHECKER_SYSTEM_PROMPT"],
            model="gpt-4o-mini",
            allowed_intercepts=[
                PyttmanPlugin.PluginInterceptPoint.before_router
            ]
        )
    )

APP_BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))

LOG_FILE_DIR = APP_BASE_DIR / Path("logs")

LOG_TO_STDOUT = True

APP_NAME = "jarvis"
APP_VERSION = "1.5.5"
DATETIME_FORMAT = "%Y-%m-%d-%H:%M"
TIMESTAMP_FORMAT = "%H:%M"

TIME_ZONE = datetime.utcnow().astimezone().tzinfo
STATIC_FILES_DIR = APP_BASE_DIR / "static"