from datetime import datetime, date
from typing import Sequence

from dateutil.relativedelta import relativedelta
from mongoengine import Q, QuerySet
from pyttman.core.ability import Ability

from jarvis.abilities.timekeeper.intents import (
    StartStopWatch,
    StopStopWatch,
    GetWorkshift,
    CreateWorkshiftsFromString
)
from jarvis.abilities.timekeeper.models import WorkShift
from jarvis.models import User


class TimeKeeper(Ability):
    intents = (StartStopWatch,
               StopStopWatch,
               GetWorkshift,
               CreateWorkshiftsFromString)

    @staticmethod
    def get_total_billable_hours(*workshifts: Sequence[WorkShift]) -> int:
        """
        Returns the total amount of billable hours for all workshifts
        provided.
        """
        billable_hours = billable_minutes = 0
        for shift in workshifts:
            duration = shift.duration
            billable_hours += duration.hour
            billable_minutes += duration.minute
            if billable_minutes >= 30:
                billable_hours += 0.5
                billable_minutes -= 30
        return billable_hours

    @classmethod
    def get_workshifts_for_current_month(cls, user: User) -> list[WorkShift]:
        """
        Get all workshifts for a user, which are all recorded in the
        current month and have been consumed,
        :param user: User owning the WorkShifts
        """
        return WorkShift.objects.filter(
            user=user,
            month=datetime.now().month,
            year=datetime.now().year
        ).all()

    @classmethod
    def get_workshifts_for_today(cls, user: User) -> list[WorkShift]:
        """
        Get all workshifts for a user, which are all recorded in the
        current month and have been consumed,
        :param user: User owning the WorkShifts
        """
        return WorkShift.objects.filter(
            user=user,
            month=datetime.now().month,
            year=datetime.now().year,
            day=datetime.now().day
        ).all()

    @classmethod
    def get_work_shifts_between_dates(cls, start_date: date,
                                      end_date: date) -> QuerySet:
        """
        Returns WorkShift objects which were created in a datetime span
        inclusively, and is consumed, meaning they're not active.

        :param start_date: The oldest day for WorkShifts to be included
        :param end_date: The most recent day for WorkShifts to be included
        """
        return WorkShift.objects.filter(year=start_date.year,
                                        end__lte=end_date,
                                        is_consumed=True)

    @staticmethod
    def get_total_billable_hours_for_month() -> int:
        pass

    @staticmethod
    def get_currently_active_workshift(user: User) -> WorkShift | None:
        """
        Returns the currently active workshift for a User,
        if there is any.
        """
        return WorkShift.objects.filter(
            Q(user=user) & Q(is_active=True)
        ).first()
