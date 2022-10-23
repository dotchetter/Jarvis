
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

import pyttman
from pyttman import app
from pyttman.core.ability import Ability
from pyttman.core.containers import Message, Reply, ReplyStream

import jarvis.abilities.timekeeper.intents as intents
from jarvis.abilities.timekeeper.models import WorkShift, Project
from jarvis.models import User


class TimeKeeper(Ability):
    intents = (intents.CreateWorkShift,
               intents.StopWorkShift,
               intents.GetWorkshift,
               intents.CreateWorkshiftsFromString,
               intents.CreateNewProject,
               intents.SetProjectAsDefault,
               intents.ActivateProject,
               intents.DeactivateProject)

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

    def save_workshift_from_string(self, message: Message):
        """
        Save a historic workshift from datetime or timestamps
        """
        current_user = User.objects.from_message(message)

        # If from->to was entered as datetime, e.g. the shift didn't occur today
        from_datetime = message.entities["from_datetime"]
        to_datetime = message.entities["to_datetime"]

        # If from->to was entered as timestamps
        from_timestamp = message.entities["from_timestamp"]
        to_timestamp = message.entities["to_timestamp"]
        project_name = message.entities["project_name"]

        if (project := Project.objects.get_by_name_or_default_project(
                project_name)) is None:
            return self.complain_no_project_was_chosen()

        workshifts_entered_as_datetime = from_datetime and to_datetime
        workshifts_entered_as_time = from_timestamp and to_timestamp

        if not (workshifts_entered_as_datetime or workshifts_entered_as_time):
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
                                 project=project,
                                 manually_created=True)

        output_start = start_datetime.strftime(app.settings.DATETIME_FORMAT)
        output_end = end_datetime.strftime(app.settings.DATETIME_FORMAT)

        return Reply(f"OK! Jag har sparat ett arbetspass med projekt {project} "
                     f"från {output_start} till {output_end} :slight_smile:")

    @classmethod
    def create_new_project(cls, message: Message) -> Reply:
        """
        Create a new project in Jarvis, to register WorkShift objects for.
        """
        if (project_name := message.entities["project_name"]) is None:
            return Reply("Du måste ange ett projektnamn.")
        if Project.objects(name=project_name.casefold()).first():
            return Reply("Det finns redan ett projekt med det namnet.")
        project = Project.objects.create(name=project_name.casefold())
        return Reply(f"Grattis till ditt nya projekt: '{project}'!")

    @classmethod
    def stop_current_workshift(cls, message: Message) -> Reply:
        """
        Stop the currently active workshift, for user
        """
        if (current_user := User.objects.from_message(message)) is None:
            return Reply("Jag vet inte vem frågan gäller?")
        if (shift := WorkShift.objects.get_active_shift_for_user(
                current_user)) is None:
            return Reply("Jag hittade inget aktivt arbetspass att avsluta")
        shift.stop()
        return Reply(f"Arbetspass avslutat. "
                     f"Passet varade {shift.duration.hour} timmar, "
                     f"{shift.duration.minute} minuter och "
                     f"{shift.duration.second} sekunder.")

    def get_worked_hours(self, message: Message) -> Reply:
        """
        Get how much the user has worked from a message,
        based on whether to sum for today or for the current month.
        """
        project_name = message.entities["project_name"]

        if (project := Project.objects.get_by_name_or_default_project(
                project_name)) is None:
            return Reply("Du har inte angivit något giltigt projekt, och "
                         "det fanns inget standardprojekt att välja. "
                         "Du kan välja mellan "
                         f"{', '.join(Project.all_project_names())}.")

        base_reply_string = "Totalt har du jobbat in {} timmar {} i projekt {}"
        current_user = User.objects.from_message(message)
        sum_for_today = message.entities["sum_for_today"]
        sum_for_month = message.entities["sum_for_month"]

        if not any((sum_for_month, sum_for_today)):
            if (active_shift := WorkShift.objects.get_active_shift_for_user(
                    current_user)) is None:
                return Reply("Du har inget aktivt arbetspass")

            shift_duration = active_shift.duration
            return Reply("Du har ett aktivt arbetspass som pågått "
                         f"{shift_duration.hour} timmar, "
                         f"{shift_duration.minute} minuter och "
                         f"{shift_duration.second} sekunder.")

        if message.entities["sum_for_today"]:
            shifts = WorkShift.objects.get_for_today_for_user_and_project(
                user=current_user,
                project=project)
            hours = self.get_total_billable_hours(*shifts)
            base_reply_string = base_reply_string.format(hours, "idag",
                                                         project)
        elif message.entities["sum_for_month"]:
            shifts = WorkShift.objects.get_all_for_user_in_current_month(
                user=current_user,
                project=project)
            hours = self.get_total_billable_hours(*shifts)
            base_reply_string = base_reply_string.format(hours, "denna månad",
                                                         project)
        return Reply(base_reply_string)

    @classmethod
    def set_project_as_default(cls, message: Message) -> Reply:
        """
        Assign a Project to be the 'default' project, as a fallback
        for intents where project is required but not mentioned
        explicitly.
        """
        project_name = message.entities["project_name"]

        if (project_by_name := Project.objects.try_get(name=project_name)) is None:
            return Reply("Jag hittade inte det projektet, "
                         "kontrollera stavningen.")

        if project_by_name.is_active is False:
            return Reply("Projektet kan inte användas som "
                         "standardprojekt eftersom det inte är aktivt.")

        for project in Project.objects.all():
            if project == project_by_name:
                project.is_default = True
            else:
                project.is_default = False
            project.save()

        return Reply(f"Jag har uppdaterat att projekt {project_name} "
                     f"är standardprojektet från och med nu. Arbetspass "
                     f"som skapas utan ett projektnamn, kommer automatiskt "
                     f"att bokföras för detta projektet.")

    @classmethod
    def get_project_by_name(cls, project_name: str) -> Project | Reply:
        """
        Get a project from name or a reply mentioning no Project was found
        """
        if (project := Project.objects.try_get(name=project_name)) is None:
            return Reply("Jag hittade inte det projektet, "
                         "kontrollera stavningen.")
        return project

    @classmethod
    def activate_project(cls, message: Message) -> Reply:
        """
        Activate a project
        """
        project_name = message.entities["project_name"]
        project: Project | Reply = cls.get_project_by_name(project_name)
        project.is_active = True
        project.save()
        return Reply(f"Projekt {project.name} är nu aktivt.")

    @classmethod
    def deactivate_project(cls, message: Message) -> Reply:
        """
        Deactivate a project
        """
        project_name = message.entities["project_name"]
        project: Project | Reply = cls.get_project_by_name(project_name)
        project.is_active = False
        project.save()
        return Reply(f"Projekt {project.name} är nu inaktivt.")

    @classmethod
    def complain_no_project_was_chosen(cls) -> ReplyStream:
        """
        Replies with a message telling that no project is active,
        and no fallback default is selected.
        """
        reply_stream = ReplyStream()
        available_projects = (str(i) for i in Project.objects.get_active())
        reply_stream.put("Du har inte angivit något giltigt projekt, "
                         "och det fanns inget standardprojekt att välja.")
        if available_projects:
            reply_stream.put("Du kan välja mellan "
                             f"{', '.join(available_projects)}.")
        return reply_stream
