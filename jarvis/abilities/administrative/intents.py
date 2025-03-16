
import pyttman
from pyttman.core.entity_parsing.fields import StringEntityField, BoolEntityField
from pyttman.core.intent import Intent
from pyttman.core.containers import (
    Message,
    Reply,
    ReplyStream
)

from jarvis.models import User, Features
from jarvis.abilities.finance.models import Expense


class UserInfo(Intent):
    """
    Returns info about the user writing the question
    """
    lead = ("berätta",)
    trail = ("mig",)
    example = "Berätta om mig"
    description = "Visar information för dig, som lagras i Jarvis!"

    def respond(self, message: Message) -> Reply | ReplyStream:
        if (user := User.objects.from_message(message)) is None:
            return Reply("Det finns ingen information om dig")

        expenses_for_user = Expense.objects.filter(user_reference=user).all()
        expenses_sum = expenses_for_user.sum("price")
        expenses_count = expenses_for_user.count()
        finance_info = f"Du har sparat {expenses_count} utgifter totalt, " \
                       f"till en totalsumma värd {expenses_sum} kronor."
        aliases = ", ".join(user.aliases)
        alias_info = f"Alias: {aliases}.\n"
        enrolled_features = (", ".join([Features(i).name
                                        for i in user.enrolled_features])) or "Inga"
        features_info = f"\nAktiverade funktioner: {enrolled_features}"

        info = (f"**Här är lite info om dig:\n\n**",
                alias_info,
                finance_info,
                features_info)
        return ReplyStream(info)


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

    def respond(self, message: Message) -> Reply | ReplyStream:
        user = User.objects.from_message(message)

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
            if feature.value not in user.enrolled_features:
                user.enrolled_features.append(feature.value)
                user.save()
            return Reply("Funktionen har aktiverats.")
        elif message.entities["deactivate_feature"]:
            if feature.value not in user.enrolled_features:
                user.enrolled_features.remove(feature.value)
            return Reply("Funktionen har inaktiverats.")
