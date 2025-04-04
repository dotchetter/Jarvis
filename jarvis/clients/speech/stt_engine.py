import io
import time

import numpy as np
import pyttman
import sounddevice as sd
from faster_whisper import WhisperModel
from pydub import AudioSegment


class SpeechToTextEngine:
    """
    Listen to the microphone and transcribe the audio using Whisper.
    """

    def __init__(self,
                 model_id,
                 audio_format=np.int16,
                 channels=1,
                 frame_rate=16000,
                 chunk_size=512,
                 volume_threshold=2000,
                 silence_duration=2,
                 hardware="cuda"):
        self.model_id = model_id
        self.audio_format = audio_format
        self.channels = channels
        self.frame_rate = frame_rate
        self.chunk_size = chunk_size
        self.volume_threshold = volume_threshold
        self.silence_duration = silence_duration
        self.hardware = hardware
        self.model = WhisperModel(
            self.model_id,
            device=self.hardware,
            compute_type="float32" if self.hardware == "cpu" else "float16",
            download_root="cache")

    def transcribe_audio(self, audio_data):
        """
        Transcribe audio data using the Whisper model.
        """
        audio = AudioSegment.from_raw(io.BytesIO(audio_data),
                                      format="raw",
                                      channels=self.channels,
                                      sample_width=2,
                                      frame_rate=self.frame_rate)

        audio_wav = io.BytesIO()
        audio.export(audio_wav, format="wav")
        audio_wav.seek(0)
        segments, info = self.model.transcribe(audio_wav,
                                               condition_on_previous_text=False)

        output = "\n".join([segment.text for segment in segments])[1:]
        return output

    def transcribe_microphone(self):
        """
        Listen to the microphone and transcribe the audio.
        """
        frames = []
        silence_count = 0
        is_recording = False
        output_text = ""

        def gibberish(text):
            """
            Determine if the microphone is picking up gibberish.
            """
            if text == "musik":
                return True
            if set(text).intersection(set("«|»<>")):
                return True

        def callback(indata, *_):
            nonlocal silence_count, is_recording, output_text

            frames.append(indata.copy())
            volume = np.max(np.abs(indata))

            if volume > self.volume_threshold:
                if not is_recording:
                    pyttman.logger.log(" - [STT]: Sound detected.")
                    is_recording = True
                silence_count = 0
            else:
                silence_count += 1

            if silence_count >= (self.silence_duration * self.frame_rate / self.chunk_size):
                if is_recording:
                    pyttman.logger.log(" - [STT]: Silence.")
                    is_recording = False
                    audio_data = np.concatenate(frames, axis=0).tobytes()
                    output_text = self.transcribe_audio(audio_data)
                    frames.clear()

        with sd.InputStream(callback=callback,
                            channels=self.channels,
                            dtype=self.audio_format,
                            samplerate=self.frame_rate,
                            blocksize=self.chunk_size):
            while True:
                if output_text:
                    break
                time.sleep(0.1)
        output = output_text if not gibberish(output_text.lower().strip()) else ""
        output = output.replace("\n", "")
        pyttman.logger.log(level="info", message=f" - [STT]: {output}")
        return output
