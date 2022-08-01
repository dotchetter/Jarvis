import sys
import speech_recognition as sr
import pyttman
from pyttman.clients.base import BaseClient
from pyttman.core.containers import Message, Reply, ReplyStream


class SpeechRecognitionClient(BaseClient):
    def run_client(self):
        print(f"\nPyttman v.{pyttman.__version__} - "
              f"CLI client", end="\n")

        print(f"{pyttman.settings.APP_NAME} is listening!\n"
              f"(?) Use Ctrl-Z or Ctrl-C plus Return to exit",
              end="\n\n")

        recognizer = sr.Recognizer()

        while True:
            try:
                with sr.Microphone() as source:
                    audio = recognizer.listen(source)

                    try:
                        recognized_speech = recognizer.recognize_sphinx(
                            audio_data=audio)
                        print("You said:", recognized_speech)
                    except sr.UnknownValueError:
                        print("Not sure what you said")
                        continue

                message = Message(recognized_speech, client=self)
                reply = self.message_router.get_reply(message)

                if isinstance(reply, ReplyStream):
                    while reply.qsize():
                        print(f"[{pyttman.settings.APP_NAME.upper()}]: ",
                              reply.get().as_str())
                else:
                    print(f"{pyttman.settings.APP_NAME}:", reply.as_str())

            except (KeyboardInterrupt, EOFError):
                sys.exit(0)
