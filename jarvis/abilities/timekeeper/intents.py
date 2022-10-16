from datetime import datetime
from decimal import Decimal

import pyttman
from mongoengine import Q
from pyttman import app
from pyttman.core.containers import ReplyStream, Reply, Message
from pyttman.core.entity_parsing.fields import BoolEntityField, \
    StringEntityField
from pyttman.core.entity_parsing.identifiers import DateTimeStringIdentifier
from pyttman.core.intent import Intent

from jarvis.abilities.timekeeper.models import WorkShift
from jarvis.custom_identifiers import TimeStampIdentifier
from jarvis.models import User


class StartStopWatch(Intent):
    """
    Starts a WorkShift or an Intermission.
    """
    lead = ("starta", "börja", "börjar", "påbörja", "ta", "tagit", "tar")
    trail = ("arbetspass", "pass", "skift", "jobb", "jobba", "arbeta")

    def respond(self, message: Message) -> Reply | ReplyStream:
        if (current_user := User.objects.from_message(message)) is None:
            return Reply("Jag vet inte vem frågan gäller?")

        if complaint := self.complain_if_workshift_exists(current_user):
            return complaint

        workshift = WorkShift.objects.create(user=current_user)
        workshift.start()
        return Reply("Okej, jag har noterat att skift har startats")

    @staticmethod
    def complain_if_workshift_exists(user: User) -> Reply | None:
        """
        Returns a Reply if the user already has an active WorkShift,
        else None.
        """
        active_shift = WorkShift.objects.filter(
            Q(user=user) & Q(is_active=True)
        ).first()

        if active_shift:
            return Reply("Du är redan i ett aktivt arbetspass som "
                         f"påbörjades {active_shift.beginning} och har pågått "
                         f"{active_shift.duration.hour} timmar, "
                         f"{active_shift.duration.minute} minuter och "
                         f"{active_shift.duration.second} sekunder.")


class StopStopWatch(Intent):
    """
    Ends a current WorkShift or Intermission.
    """
    lead = ("avsluta", "stanna", "sluta", "slutar",
            "stopp", "stoppa", "ta", "tagit", "tar")
    trail = ("arbetspass", "pass", "skift", "jobb", "jobba",
             "arbeta", "rast", "paus", "lunch", "vila", "rasten",
             "jag")

    def respond(self, message: Message) -> Reply | ReplyStream:
        if (current_user := User.objects.from_message(message)) is None:
            return Reply("Jag vet inte vem frågan gäller?")

        shift: WorkShift = WorkShift.objects.filter(
            Q(user=current_user) & Q(is_active=True)
        ).first()

        if shift is None:
            return Reply("Jag hittade inget aktivt arbetspass att avsluta")
        shift.stop()
        return Reply(f"Arbetspass avslutat. "
                     f"Passet varade {shift.duration.hour} timmar, "
                     f"{shift.duration.minute} minuter och "
                     f"{shift.duration.second} sekunder.")


class GetWorkshift(Intent):
    """
    Get information about a currently running work shift.
    """
    lead = ("visa", "hämta", "hur",)
    trail = ("pass", "arbetspass", "skift", "timmar", "jobbat")

    sum_for_today = BoolEntityField(message_contains=("idag", "idag?"))
    sum_for_month = BoolEntityField(message_contains=("månad", "månaden",
                                                      "månad?", "månaden?"))

    def respond(self, message: Message) -> Reply | ReplyStream:
        base_reply_string = "Totalt har du jobbat in {} timmar {}"
        current_user = User.objects.from_message(message)
        sum_for_today = message.entities["sum_for_today"]
        sum_for_month = message.entities["sum_for_month"]
        if not any((sum_for_month, sum_for_today)):
            if (active_shift := self.ability.get_currently_active_workshift(
                    current_user)) is None:
                return Reply("Du har inget aktivt arbetspass")
            shift_duration = active_shift.duration
            return Reply("Du har ett aktivt arbetspass som pågått "
                         f"{shift_duration.hour} timmar, "
                         f"{shift_duration.minute} minuter och "
                         f"{shift_duration.second} sekunder.")

        if message.entities["sum_for_today"] is True:
            shifts = self.ability.get_workshifts_for_today(current_user)
            hours = self.ability.get_total_billable_hours(*shifts)
            base_reply_string = base_reply_string.format(hours, "idag")
        elif message.entities["sum_for_month"] is True:
            shifts = self.ability.get_workshifts_for_current_month(current_user)
            hours = self.ability.get_total_billable_hours(*shifts)
            base_reply_string = base_reply_string.format(hours, "denna månad")
        return Reply(base_reply_string)


class CreateWorkshiftsFromString(Intent):

    lead = ("lägg", "spara", "skapa", "nytt")
    trail = ("pass", "arbetspass", "skift", "timmar")

    from_datetime = StringEntityField(identifier=DateTimeStringIdentifier)
    to_datetime = StringEntityField(identifier=DateTimeStringIdentifier)

    from_timestamp = StringEntityField(identifier=TimeStampIdentifier)
    to_timestamp = StringEntityField(identifier=TimeStampIdentifier)

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.save_workshift_from_string(message)
