import io
import os

import pygame
from openai import OpenAI


class TextToSpeechEngine:
    """
    Convert text to speech using OpenAI's API.
    """
    def __init__(self,
                 model: str,
                 voice: str,
                 speed: str | int | float = 1.0):
        self.model = model
        self.voice = voice
        self.speed = speed

    def say(self, text):
        """
        Convert text to speech and play the audio.
        """
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.audio.speech.create(
            model=self.model,
            voice=self.voice,
            speed=float(self.speed),
            input=text)

        pygame.mixer.init()
        pygame.mixer.music.load(io.BytesIO(response.content))
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.quit()
