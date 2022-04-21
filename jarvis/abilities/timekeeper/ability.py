from datetime import datetime

from mongoengine import Q
from pyttman.core.ability import Ability

from jarvis.abilities.timekeeper.models import WorkShift
from jarvis.models import User
from jarvis.abilities.timekeeper.intents import (
    StartStopWatch, StopStopWatch, GetWorkshift
)


class TimeKeeper(Ability):
    intents = (StartStopWatch, StopStopWatch, GetWorkshift)

    @staticmethod
    def get_total_billable_hours(message) -> int:
        """
        Sums up the committed workshifts for the current user for today,
        and sums up the total amount of billable hours for all workshifts
        registered this same day.
        """
        today = datetime.now().date()
        billable_hours, billable_minutes = 0, 0
        current_user = User.objects.from_message(message)
        workshifts = WorkShift.objects.filter(
            Q(user=current_user) & Q(is_consumed=True) & Q(created_date=today)
        ).all()

        for shift in workshifts:
            duration = shift.duration
            billable_hours += duration.hour
            billable_minutes += duration.minute
            if billable_minutes >= 30:
                billable_hours += 0.5
                billable_minutes -= 30
        return billable_hours

    @staticmethod
    def get_currently_active_workshift(message) -> WorkShift | None:
        """
        Returns the currently active workshift for a User,
        if there is any.
        """
        current_user = User.objects.from_message(message)
        return WorkShift.objects.filter(
            Q(user=current_user) & Q(is_active=True)
        ).first()
