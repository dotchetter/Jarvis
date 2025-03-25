from time import sleep

import pyttman
from pyttman.core.containers import Reply, ReplyStream, Message
from pyttman.core.entity_parsing.fields import StringEntityField
from pyttman.core.intent import Intent


class PlaySpotify(Intent):
    """
    Start playback on spotify.
    """
    lead = ("spela", "spelar")
    trail = ("spotify", "spotify.")
    exclude_trail_in_entities = True

    song_name = StringEntityField(span=5, exclude=("på",))
    artist = StringEntityField(prefixes=("av", "med"), span=10, exclude=("på",))

    def respond(self, message: Message) -> Reply | ReplyStream:
        """
        Start playback on spotify.
        """
        if user_disabled := self.ability.assert_user_enabled(message.user):
            return user_disabled
        if (song_name := message.entities["song_name"]) is None:
            self.ability.play(device_id=self.storage["device_id"])
            return Reply("Ok, jag har startat musiken.")

        artist = message.entities.get("artist")

        if song_name and artist:
            query = f"track:{song_name} artist:{artist}"
        else:
            query = song_name

        try:
            result = self.ability.search(query)["tracks"]
            items = result["items"]
            uri = items[0]["uri"]
        except (KeyError, IndexError):
            return Reply("Jag hittade ingen låt som matchade "
                         "det du sökte på... prova igen!")
        try:
            self.ability.play(device_id=self.storage["device_id"],
                              song_uri=[uri])
            sleep(1)
            now_playing = self.ability.now_playing()
            track = now_playing["item"]["name"]
            artist = now_playing["item"]["artists"][0]["name"]
            return Reply(f"Nu spelas {track} av {artist}.")
        except Exception as e:
            pyttman.logger.log(level="error", message=e)
            return Reply(f"Nåt gick fel, jag kunde tyvärr inte spela "
                         f"musik. Prova lite senare.")


class PauseSpotify(Intent):
    """
    Pause playback on spotify.
    """
    lead = ("pausa",)
    trail = ("musik", "låt", "spotify", "musiken")

    def respond(self, message: Message) -> Reply | ReplyStream:
        """
        Pause playback on spotify.
        """
        if user_disabled := self.ability.assert_user_enabled(message.user):
            return user_disabled
        if not self.ability.now_playing():
            return Reply("Det spelas ingen musik just nu.")
        self.ability.pause()
        return Reply("Jag har pausat musiken.")


class IncreaseVolumeSpotify(Intent):
    """
    Increase volume on spotify.
    """
    lead = ("höj", "öka")
    trail = ("volymen", "volym", "ljudet")

    def respond(self, message: Message) -> Reply | ReplyStream:
        """
        Increase volume on spotify.
        """
        if user_disabled := self.ability.assert_user_enabled(message.user):
            return user_disabled
        if not self.ability.current_device():
            return Reply("Det finns ingen enhet att justera volymen på.")
        if not self.ability.now_playing():
            return Reply("Det spelas ingen musik just nu.")
        self.ability.volume_up()
        return Reply("Jag har höjt volymen.")


class DecreaseVolumeSpotify(Intent):
    """
    Decrease volume on spotify.
    """
    lead = ("sänk", "minska",)
    trail = ("volymen", "volym", "ljudet")

    def respond(self, message: Message) -> Reply | ReplyStream:
        """
        Decrease volume on spotify.
        """
        if user_disabled := self.ability.assert_user_enabled(message.user):
            return user_disabled
        if not self.ability.current_device():
            return Reply("Det finns ingen enhet att justera volymen på.")
        if not self.ability.now_playing():
            return Reply("Det spelas ingen musik just nu.")
        self.ability.volume_down()
        return Reply("Jag har sänkt volymen.")


class NextSpotify(Intent):
    """
    Skip to next track on spotify.
    """
    lead = ("nästa",)
    trail = ("låt", "spår", "musik")

    def respond(self, message: Message) -> Reply | ReplyStream:
        """
        Skip to next track on spotify.
        """
        if user_disabled := self.ability.assert_user_enabled(message.user):
            return user_disabled
        if not self.ability.now_playing():
            return Reply("Det spelas ingen musik just nu.")
        self.ability.next()
        return Reply("Ok!")


class PreviousSpotify(Intent):
    """
    Skip to previous track on spotify.
    """
    lead = ("föregående",)
    trail = ("låt", "spår", "musik")
    ordered = True

    def respond(self, message: Message) -> Reply | ReplyStream:
        """
        Skip to previous track on spotify.
        """
        if user_disabled := self.ability.assert_user_enabled(message.user):
            return user_disabled
        if not self.ability.now_playing():
            return Reply("Det spelas ingen musik just nu.")
        self.ability.previous()
        return Reply("Ok!")


class WhatIsPlayingSpotify(Intent):
    """
    Get information about the current track playing on spotify.
    """
    exact_match = ("vad", "spelas", "just", "nu")
    ordered = True

    def respond(self, message: Message) -> Reply | ReplyStream:
        """
        Get information about the current track playing on spotify.
        """
        if user_disabled := self.ability.assert_user_enabled(message.user):
            return user_disabled
        now_playing = self.ability.now_playing()
        if not now_playing:
            return Reply("Det spelas ingen musik just nu.")
        track = now_playing["item"]["name"]
        artist = now_playing["item"]["artists"][0]["name"]
        return Reply(f"Just nu spelas {track} av {artist}.")
