import os

import pyttman.core.containers
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
    feature_name = StringEntityField(valid_strings=[i.name for i in Features])
    password = StringEntityField(prefixes=("lösenord", "password"))
    _feature_class_map = {
        "utgift": Features.shared_finances,
        "utgifter": Features.shared_finances,
        "tidsstämpel": Features.timekeeper,
        "spotify": Features.spotify}

    def respond(self, message: pyttman.core.containers.Message) -> pyttman.core.containers.Reply:

        if not (feature_name := message.entities["feature_name"]):
            return pyttman.core.containers.Reply("Du har angett ett felaktigt namn på "
                         "funktionen du vill aktivera. "
                         "Tillgängliga alternativ är: "
                         f"{self.feature_name.valid_strings}")

        password = message.entities["password"]
        try:
            feature = self._feature_class_map[feature_name.lower().strip()]
        except KeyError as e:
            print(e)
            return pyttman.core.containers.Reply("Något blev fel, jag kunde inte aktivera "
                         "funktionen. Försök igen senare.")

        if message.entities["activate_feature"]:
            if feature.is_private(feature) and password != os.environ["PRIVATE_FEATURE_PASSWORD"]:
                return pyttman.core.containers.Reply("Fel lösenord, försök igen.")
            if feature.value not in message.user.enrolled_features:
                message.user.enrolled_features.append(feature.value)
                message.user.save()
            return pyttman.core.containers.Reply("Funktionen har aktiverats.")
        elif message.entities["deactivate_feature"]:
            if feature.value not in message.user.enrolled_features:
                message.user.enrolled_features.remove(feature.value)
            return pyttman.core.containers.Reply("Funktionen har inaktiverats.")
