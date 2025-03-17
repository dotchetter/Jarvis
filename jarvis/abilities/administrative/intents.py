from pyttman.core.containers import (
    Message,
    Reply,
    ReplyStream
)
from pyttman.core.entity_parsing.fields import StringEntityField, BoolEntityField
from pyttman.core.intent import Intent

from jarvis.models import Features


class UserFeatureEnrollment(Intent):
    """
    This intent allows users to enrol and disenrol to features in
    Jarvis.
    """
    lead = ("aktivera", "deaktivera", "inaktivera", "avaktivera")
    trail = ("funktion", "funktionen", "app", "appen")
    exclude_lead_in_entities = False
    exclude_trail_in_entities = False
    activate_feature = BoolEntityField(message_contains=("aktivera", "på"))
    deactivate_feature = BoolEntityField(message_contains=("avaktivera",
                                                           "deaktivera",
                                                           "inaktivera",
                                                           "av"))
    feature_name = StringEntityField(valid_strings=("utgifter",
                                                    "utgift",
                                                    "tidsstämpel"))
    _feature_class_map = {
        "utgift": Features.shared_finances,
        "utgifter": Features.shared_finances,
        "tidsstämpel": Features.timekeeper}

    def respond(self, message: Message) -> Reply:

        if not (feature_name := message.entities["feature_name"]):
            return Reply("Du har angett ett felaktigt namn på "
                         "funktionen du vill aktivera. "
                         "Tillgängliga alternativ är: "
                         f"{self.feature_name.valid_strings}")

        try:
            feature = self._feature_class_map[feature_name]
        except KeyError:
            return Reply("Något blev fel, jag kunde inte aktivera "
                         "funktionen. Försök igen senare.")

        if message.entities["activate_feature"]:
            if feature.value not in message.user.enrolled_features:
                message.user.enrolled_features.append(feature.value)
                message.user.save()
            return Reply("Funktionen har aktiverats.")
        elif message.entities["deactivate_feature"]:
            if feature.value not in message.user.enrolled_features:
                message.user.enrolled_features.remove(feature.value)
            return Reply("Funktionen har inaktiverats.")
