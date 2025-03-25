import os
import re
import string
import sys
from time import time

import pyttman
from fuzzywuzzy import fuzz
from pyttman import logger as logger
from pyttman.clients.base import BaseClient
from pyttman.core.containers import Message, ReplyStream

from jarvis.clients.speech.stt_engine import SpeechToTextEngine
from jarvis.clients.speech.tts_engine import TextToSpeechEngine


class SpeechClient(BaseClient):
    """
    This client uses speech recognition to listen for user input
    The input is transcribed, processed and a reply is generated.
    The reply is then read out to the user.
    """
    def __init__(self,
                 greeting_message: str,
                 silence_seconds_before_processing: int = 2,
                 silence_seconds_before_standby: int = 60,
                 standby_mode_message: str = None,
                 name_similarity_threshold_percent: float = 50,
                 volume_threshold: int = 2000,
                 mute_word: str = "mute",
                 user_name_prompt: str = "What's your name?",
                 **kwargs):

        self.user_name_prompt = user_name_prompt
        self.greeting_message = greeting_message
        self.silence_seconds_before_standby = int(silence_seconds_before_standby)
        self.name_similarity_threshold_percent = int(name_similarity_threshold_percent)
        self.standby_mode_message = standby_mode_message
        self.mute_word = mute_word

        self.stt_client = SpeechToTextEngine(
            silence_duration=int(silence_seconds_before_processing),
            volume_threshold=int(volume_threshold),
            model_id=os.environ["STT_MODEL_ID"])
        self.tts_client = TextToSpeechEngine(
            model=os.environ["TTS_MODEL"],
            voice=os.environ["TTS_VOICE"],
            speed=os.environ["TTS_SPEED"])

        super().__init__(**kwargs)

    def authorize(self) -> tuple[str, str]:

        def read_microphone():
            return self.stt_client.transcribe_microphone().lower().strip().replace(".", "")

        self.tts_client.say("Hi! Whats your name?")
        user_name = read_microphone()
        logger.log(f" - user_name: {user_name}")

        while not (user_alias := os.getenv(user_name)):
            self.tts_client.say(f"Sorry, I don't know you."
                           f"Only registered people can use this system. "
                           f"Did I get your name wrong? Answer yes or no.")
            if "yes" in read_microphone():
                self.tts_client.say("Sorry about that, let's try again. What's your name?")
                user_name = read_microphone()
            else:
                self.tts_client.say("Sorry, I can't help you. Goodbye.")
                sys.exit(0)
        return user_name, user_alias


    def run_client(self):
        user_name = os.getenv("STT_USER_NAME", "")
        print(f"\nPyttman v.{pyttman.__version__} - "
              f"Speech client", end="\n")

        while not (user_alias := os.getenv(user_name.lower())):
            self.tts_client.say(self.user_name_prompt)
            user_name = self.stt_client.transcribe_microphone().lower().strip()
            user_name = re.sub(f"[{string.punctuation}]", "", user_name)

        print(f"{pyttman.settings.APP_NAME} is listening!\n"
              f"(?) Use Ctrl-Z or Ctrl-C plus Return to exit",
              end="\n\n")

        self.tts_client.say(f"{pyttman.settings.APP_NAME} is online.")
        self.tts_client.say(self.greeting_message.format(user_name))

        dialog_refreshed = time()
        muted = False

        def text_contains_unmute(text):
            # Remove all chars except letters and spaces

            app_name = pyttman.settings.APP_NAME.lower()
            for word in text.lower().strip().split():
                similarity = fuzz.ratio(word, app_name)
                print("word:", word, "check", app_name, "similarity:", similarity)
                if similarity >= self.name_similarity_threshold_percent:
                    return True
            return False

        def text_contains_mute(text):
            return self.mute_word in text.lower().strip()

        while True:
            try:
                if not (text := self.stt_client.transcribe_microphone()):
                    continue

                cleaned_text = re.sub(f"[{re.escape(string.punctuation)}]", "", text).strip().lower()
                if not muted and text_contains_mute(cleaned_text):
                    muted = True
                    logger.log(f" - [SpeechClient]: Muted.")
                    continue
                elif muted and text_contains_unmute(cleaned_text):
                    dialog_refreshed = time()
                    muted = False

                timeout_reached = (time() - dialog_refreshed > 120)
                if timeout_reached or muted:
                    continue

                message = Message(text, client=self)
                message.author.id = user_alias
                reply = self.message_router.get_reply(message)

                if isinstance(reply, ReplyStream):
                    while reply.qsize():
                        self.tts_client.say(reply.get())
                    dialog_refreshed = time()
                else:
                    self.tts_client.say(reply.as_str())
                    dialog_refreshed = time()


            except (KeyboardInterrupt, EOFError):
                logger.log("\n- [SpeechClient]: Exiting..")
                self.tts_client.say("AI systems shutting down.")
                sys.exit(0)
