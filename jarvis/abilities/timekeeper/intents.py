from mongoengine import Q
from pyttman.core.containers import ReplyStream, Reply, Message
from pyttman.core.entity_parsing.fields import BoolEntityField
from pyttman.core.intent import Intent

from jarvis.abilities.timekeeper.models import WorkShift
from jarvis.models import User


class StartStopWatch(Intent):
    """
    Starts a WorkShift or an Intermission.
    """
    lead = ("starta", "börja", "börjar", "påbörja", "ta", "tagit", "tar")
    trail = ("arbetspass", "pass", "skift", "jobb", "jobba", "arbeta")

    def respond(self, message: Message) -> Reply | ReplyStream:
        if current_user := User.objects.from_message(message) is None:
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
    lead = ("avsluta", "stanna", "sluta", "stopp",
            "stoppa", "ta", "tagit", "tar")
    trail = ("arbetspass", "pass", "skift", "jobb", "jobba",
             "arbeta", "rast", "paus", "lunch", "vila", "rasten")

    def respond(self, message: Message) -> Reply | ReplyStream:
        if current_user := User.objects.from_message(message) is None:
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
    lead = ("visa", "hämta",)
    trail = ("pass", "arbetspass", "skift",)

    sum_for_today = BoolEntityField(
        message_contains=("totalt", "total", "summa")
    )

    def respond(self, message: Message) -> Reply | ReplyStream:
        if message.entities["sum_for_today"] is True:
            hours = self.ability.get_total_billable_hours(message)
            return Reply(f"Totalt har du arbetat in {hours} timmar idag.")

        workshift = self.ability.get_currently_active_workshift(message)
        if workshift is None:
            return Reply("Du har inget aktivt arbetspass")

        shift_duration = workshift.duration
        return Reply("Du har ett aktivt arbetspass som pågått "
                     f"{shift_duration.hour} timmar, "
                     f"{shift_duration.minute} minuter och "
                     f"{shift_duration.second} sekunder.")