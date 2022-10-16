from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

import pyttman
from mongoengine import Q, QuerySet
from pyttman import app
from pyttman.core.ability import Ability
from pyttman.core.containers import Message, Reply

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

    def before_create(self):
        pass #WorkShift.time_zone = app.settings.TIME_ZONE

    @staticmethod
    def get_total_billable_hours(*workshifts: Sequence[WorkShift]) -> Decimal:
        """
        Returns the total amount of billable hours for all workshifts
        provided.
        """
        billable_hours = billable_minutes = 0
        for shift in workshifts:
            duration = shift.duration
            billable_hours += duration.hour
            billable_minutes += duration.minute
        billable_hours += billable_minutes / 60
        return Decimal(billable_hours).quantize(Decimal('.00'),
                                                rounding=ROUND_HALF_UP)

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
    def get_currently_active_workshift(user: User) -> WorkShift | None:
        """
        Returns the currently active workshift for a User,
        if there is any.
        """
        return WorkShift.objects.filter(
            Q(user=user) & Q(is_active=True)
        ).first()

    @staticmethod
    def save_workshift_from_string(message: Message):
        current_user = User.objects.from_message(message)

        # If from->to was entered as datetime, e.g. the shift didn't occur today
        from_datetime = message.entities["from_datetime"]
        to_datetime = message.entities["to_datetime"]

        # If from->to was entered as timestamps
        from_timestamp = message.entities["from_timestamp"]
        to_timestamp = message.entities["to_timestamp"]

        if not ((from_datetime and to_datetime) or (from_timestamp and to_timestamp)):
            return Reply("Ange när arbetspasset började och slutade. "
                         "Om båda dessa infaller idag, räcker det med "
                         "klockslag, t.ex. `08:30 till 12:00`.")

        if from_datetime and to_datetime:
            dt_format = app.settings.DATETIME_FORMAT
            start_datetime = datetime.strptime(from_datetime, dt_format)
            end_datetime = datetime.strptime(to_datetime, dt_format)
        else:
            dt_format = app.settings.TIMESTAMP_FORMAT
            start_datetime = end_datetime = datetime.now()
            timestamp_start = datetime.strptime(from_timestamp, dt_format)
            timestamp_end = datetime.strptime(to_timestamp, dt_format)

            start_datetime = start_datetime.replace(hour=timestamp_start.hour,
                                                    minute=timestamp_start.minute)
            end_datetime = end_datetime.replace(hour=timestamp_end.hour,
                                                minute=timestamp_end.minute)

        try:
            if start_datetime > end_datetime:
                return Reply("Felaktigt inmatade värden: Passet kan inte "
                             "sluta innan det börjat. Det blir ju lite "
                             "konstigt?")
        except Exception as e:
            pyttman.logger.log(str(e), "error")
            return Reply("Jag kunde inte förstå när "
                         "passet började och slutade..")

        WorkShift.objects.create(user=current_user,
                                 is_active=False,
                                 is_consumed=True,
                                 beginning=start_datetime,
                                 end=end_datetime,
                                 year=start_datetime.year,
                                 day=start_datetime.day,
                                 month=start_datetime.month,
                                 manually_created=True)

        output_start = start_datetime.strftime(app.settings.DATETIME_FORMAT)
        output_end = end_datetime.strftime(app.settings.DATETIME_FORMAT)

        return Reply("OK! Jag har sparat ett arbetspass från "
                     f"{output_start} till {output_end} :slight_smile:")
