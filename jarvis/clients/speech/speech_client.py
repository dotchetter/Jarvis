import os
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
                 **kwargs):

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
        """
        Listen for user input, process it and generate a reply.
        """
        user_name, user_alias = self.authorize()
        dialog_refreshed = time()
        standby_announced = False
        muted = False

        logger.log(f"\nPyttman v.{pyttman.__version__} - CLI client")
        logger.log(f"{pyttman.settings.APP_NAME} is listening!\n"
              f"(?) Use Ctrl-Z or Ctrl-C plus Return to exit")

        def talking_to_me(text):
            """
            Determine if a human is talking to us, the AI.
            """
            for word in text.lower().strip().split():
                word = word.translate(str.maketrans("", "", string.punctuation))
                percent = fuzz.ratio(word, pyttman.app.settings.APP_NAME)
                if percent >= self.name_similarity_threshold_percent:
                    return True
            return False

        def trigger_mute(text):
            """
            Determine if the user wants to mute the AI.
            """
            return self.mute_word in text.lower().strip()

        def silence_standby():
            """
            Determine if the user is silent for too long.
            """
            return (time() - dialog_refreshed >
                    self.silence_seconds_before_standby)

        self.tts_client.say(self.greeting_message.format(user_name))

        while True:
            try:
                if text := self.stt_client.transcribe_microphone():

                    if text.startswith("«") or text.startswith("»"):
                        continue

                    if trigger_mute(text) or silence_standby():
                        muted = True

                    if muted and not talking_to_me(text) or muted:
                        if not standby_announced:
                            logger.log(f" - [{pyttman.app.settings.APP_NAME}]: "
                                       f"Stopped listening, call me by my name to "
                                       f"continue conversation.")
                            self.tts_client.say(self.standby_mode_message)
                            standby_announced = True
                        continue

                    standby_announced = False
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
