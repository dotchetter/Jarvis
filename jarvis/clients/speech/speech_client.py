import os
import sys
from time import time

import pyttman
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

    def run_client(self):
        user_alias = input("\n\n-> Enter username: ")
        print(f"\nPyttman v.{pyttman.__version__} - "
              f"CLI client", end="\n")

        print(f"{pyttman.settings.APP_NAME} is listening!\n"
              f"(?) Use Ctrl-Z or Ctrl-C plus Return to exit",
              end="\n\n")
        stt_client = SpeechToTextEngine(silence_threshold=3000)
        tts_client = TextToSpeechEngine()
        dialog_refreshed = time()

        def text_contains_jarvis(text):
            text = text.lower()
            if "jarvis" in text:
                return True
            if "jervis" in text:
                return True
            if "gervis" in text:
                return True
            if "jarbis" in text:
                return True
            return False

        while True:
            try:
                if text := stt_client.transcribe_microphone():
                    if text.startswith("«") or text.startswith("»"):
                        continue

                    require_keyword = (time() - dialog_refreshed > 60)
                    if require_keyword and not text_contains_jarvis(text):
                        print("Ignoring dialogue, address me by name to unlock.")
                        continue

                    message = Message(text, client=self)
                    message.author.id = user_alias
                    reply = self.message_router.get_reply(message)

                    if isinstance(reply, ReplyStream):
                        while reply.qsize():
                            tts_client.say(reply.get())
                        dialog_refreshed = time()
                    else:
                        tts_client.say(reply.as_str())
                        dialog_refreshed = time()


            except (KeyboardInterrupt, EOFError):
                sys.exit(0)
