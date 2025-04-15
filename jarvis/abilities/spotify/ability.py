import os

import spotipy
from pyttman import app
from pyttman.core.ability import Ability
from spotipy import SpotifyOAuth

from jarvis.abilities.spotify.intents import *
from jarvis.models import Features


class SpotifyAbility(Ability):
    """
    Interface with Spotify, a wrapper on the pre-existing spotpy library
    """
    spotify: spotipy.Spotify
    intents = (
        PlaySpotify,
        PauseSpotify,
        IncreaseVolumeSpotify,
        DecreaseVolumeSpotify,
        NextSpotify,
        PreviousSpotify,
        WhatIsPlayingSpotify,
        ListAvailableDevices
    )

    def before_create(self):
        auth_manager = SpotifyOAuth(client_id=os.environ["SPOTIFY_CLIENT_ID"],
                                    client_secret=os.environ["SPOTIFY_API_KEY"],
                                    redirect_uri=os.environ["SPOTIFY_REDIRECT_URL"],
                                    scope=os.environ["SPOTIFY_ACCESS_SCOPE"])
        self.spotify = spotipy.Spotify(auth_manager=auth_manager)
        self.storage["access_token"] = self.spotify.auth_manager.get_access_token()
        self.storage["device_id"] = os.environ["SPOTIFY_DEVICE_ID"]

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
        app.client.muted = True

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