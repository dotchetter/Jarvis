import os
import tempfile
from pathlib import Path

import pygame
from dotenv import load_dotenv
from openai import OpenAI


class TextToSpeechEngine:

    def say(self, text):
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        speech_file_path = "speech.mp3"

        with tempfile.TemporaryDirectory() as tempdir:
            speech_file_path = Path(tempdir) / Path(speech_file_path)
            response = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=text)

            response.stream_to_file(speech_file_path)
            pygame.mixer.init()
            pygame.mixer.music.load(speech_file_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            pygame.mixer.music.stop()
            pygame.mixer.quit()


if __name__ == "__main__":
    load_dotenv()
    tts_client = TextToSpeechEngine()
    tts_client.say("Hej, jag heter Jarvis. Vad kan jag hjälpa dig med idag?")