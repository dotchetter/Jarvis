from pyttman.core.containers import Message, Reply, ReplyStream
from pyttman.core.entity_parsing.fields import DecimalEntityField
from pyttman.core.intent import Intent

from jarvis.abilities.weightkeeper.models import WeightEntry
from jarvis.models import User


class EnterWeight(Intent):
    """
    Allows the user to enter their weight, to store.
    """
    lead = ("våg", "vägde", "vikt", "tung", "väger")

    weight_in_kilos = DecimalEntityField()

    def respond(self, message: Message) -> Reply | ReplyStream:
        if (weight := message.entities["weight_in_kilos"]) is None:
            return Reply("Vad väger du?")
        WeightEntry.objects.create(kilos=weight, user=message.user)
        response = f"Vikt sparad: {weight} kg"
        return Reply(response)

