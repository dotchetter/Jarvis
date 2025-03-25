import os

import spotipy
from pyttman.core.ability import Ability
from spotipy import SpotifyOAuth

from jarvis.abilities.musicplayer.intents import *
from jarvis.models import Features


class SpotifyAbility(Ability):
    """
    Interface with Spotify, a wrapper on the pre-existing spotpy library
    """
    ready = False
    auth_manager: SpotifyOAuth
    spotify: spotipy.Spotify
    intents = (
        LoginSpotify,
        PlaySpotify,
        PauseSpotify,
        IncreaseVolumeSpotify,
        DecreaseVolumeSpotify,
        NextSpotify,
        PreviousSpotify,
        WhatIsPlayingSpotify,
    )

    def before_create(self):
        auth_manager = SpotifyOAuth(client_id=os.environ["SPOTIFY_CLIENT_ID"],
                                    client_secret=os.environ["SPOTIFY_API_KEY"],
                                    redirect_uri=os.environ["SPOTIFY_REDIRECT_URL"],
                                    scope=os.environ["SPOTIFY_ACCESS_SCOPE"])
        self.storage["device_id"] = os.environ["SPOTIFY_DEVICE_ID"]
        self.auth_manager = auth_manager
        self.spotify = spotipy.Spotify(auth_manager=auth_manager)

    def get_auth_url(self):
        url = self.auth_manager.get_authorize_url()
        return Reply("Du måste ge mig åtkomst till ditt konto först. Öppna denna länk i din webbläsare. "
                     "Vänta en liten stund. Kopiera sedan länken som står i din webbläsares adressfält "
                     "efter en stund, även om du får ett felmeddelande.\n\nSvara detta meddelande med "
                     f"logga in på spotify med länk' följt av länken, för att logga in på Spotify.\n\n {url}")

    def set_auth_code(self, auth_code):
        token_data = self.spotify.auth_manager.get_access_token(auth_code)
        access_token = token_data["access_token"]
        self.spotify = spotipy.Spotify(auth=access_token)
        self.storage["access_token"] = access_token
        self.ready = True

    def devices_available(self):
        return self.spotify.devices()

    def now_playing(self):
        return self.spotify.current_playback()

    def current_device(self):
        if self.spotify.current_playback() is None:
            return None
        return self.spotify.current_playback()["device"]

    def get_saved_tracks(self):
        return self.spotify.current_user_saved_tracks()

    def get_saved_albums(self):
        return self.spotify.current_user_saved_albums()

    def pause(self):
        self.spotify.pause_playback()

    def play(self, device_id=None, song_uri=None):
        self.spotify.start_playback(device_id=device_id, uris=song_uri)

    def next(self):
        self.spotify.next_track()

    def previous(self):
        self.spotify.previous_track()

    def search(self, query):
        result = self.spotify.search(q=query)
        return result

    def volume_up(self):
        current_volume = self.spotify.current_playback()["device"]["volume_percent"]
        if current_volume < 100:
            current_volume += 10
            self.spotify.volume(current_volume)

    def volume_down(self):
        current_volume = self.spotify.current_playback()["device"]["volume_percent"]
        if current_volume > 0:
            current_volume -= 10
            self.spotify.volume(current_volume)

    @staticmethod
    def assert_user_enabled(user) -> Reply or None:
        if not user.feature_enabled(Features.spotify):
            return Reply("Du har inte aktiverat Spotify-funktionen. "
                         "Säg 'aktivera funktionen Spotify' för att aktivera den."
                         "Om funktionen är privat, kan du behöva ange ett lösenord. "
                         "Ange lösenordet efter frasen 'lösenord' när du aktiverar"
                         "funktionen.")
        return None