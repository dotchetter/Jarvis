from datetime import datetime

from pyttman import app
from pyttman.core.containers import ReplyStream, Reply, Message
from pyttman.core.entity_parsing.fields import BoolEntityField, \
    StringEntityField, IntEntityField
from pyttman.core.entity_parsing.identifiers import DateTimeStringIdentifier
from pyttman.core.intent import Intent

from jarvis.abilities.finance.month import Month
from jarvis.abilities.timekeeper.models import WorkShift, Project
from jarvis.custom_identifiers import TimeStampIdentifier
from jarvis.models import User


class CreateWorkShift(Intent):
    """
    Starts a WorkShift or an Intermission.
    """
    exact_match = ("jag", "börjar", "jobba")
    project_name = StringEntityField(valid_strings=Project.all_project_names)

    def respond(self, message: Message) -> Reply | ReplyStream:
        project_name = message.entities["project_name"]

        if message.user is None:
            return Reply("Jag vet inte vem frågan gäller?")
        if complaint := self.complain_if_workshift_exists(message.user):
            return complaint
        if (project := Project.objects.get_by_name_or_default_project(
                project_name)) is None:
            return self.ability.complain_no_project_was_chosen()

        WorkShift.objects.create(user=message.user, project=project).start()
        return Reply(f"Ett skift startades för projektet {project}.")

    @staticmethod
    def complain_if_workshift_exists(user: User) -> Reply | None:
        """
        Returns a Reply if the user already has an active WorkShift,
        else None.
        """
        if active_shift := WorkShift.objects.get_active_shift_for_user(user):
            return Reply("Du är redan i ett aktivt arbetspass som "
                         f"påbörjades {active_shift.beginning} och har pågått "
                         f"{active_shift.duration.hour} timmar, "
                         f"{active_shift.duration.minute} minuter och "
                         f"{active_shift.duration.second} sekunder, på "
                         f"projekt {active_shift.project.name}.")


class StopWorkShift(Intent):
    """
    Ends a current WorkShift or Intermission.
    """
    exact_match = ("nu", "slutar", "jag")

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.stop_current_workshift(message)


class GetWorkShift(Intent):
    """
    Get information about a currently running work shift.
    """
    lead = ("visa", "hämta", "hur",)
    trail = ("pass", "arbetspass", "skift", "timmar", "jobbat", "tjänat")

    sum_for_today = BoolEntityField(message_contains=("idag", "idag?"))
    sum_for_month = BoolEntityField(message_contains=("månad", "månaden",
                                                      "månad?", "månaden?"))
    project_name = StringEntityField(valid_strings=Project.all_project_names)

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.get_worked_hours(message)


class CreateWorkShiftFromString(Intent):
    """
    Store a work shift by entering timestamp
    or datetime stamps manually.
    """
    help_string = __doc__
    lead = ("lägg", "spara", "skapa", "nytt")
    trail = ("pass", "arbetspass", "skift", "timmar")

    from_datetime = StringEntityField(identifier=DateTimeStringIdentifier)
    to_datetime = StringEntityField(identifier=DateTimeStringIdentifier)
    from_timestamp = StringEntityField(identifier=TimeStampIdentifier)
    to_timestamp = StringEntityField(identifier=TimeStampIdentifier)
    project_name = StringEntityField(valid_strings=Project.all_project_names)
    until_now = BoolEntityField(message_contains=("nu",))

    def respond(self, message: Message) -> Reply | ReplyStream:
        try:
            return self.ability.save_workshift_from_string(message)
        except ValueError:
            return Reply("Jag kunde inte spara arbetspasset. Om det inte förekom "
                         "idag, behöver du ange datum. år-månad-dag-timme-minut. "
                         f"Det jag fick var:\n*{message.as_str()}*")



class CreateNewProject(Intent):
    """
    Create a new Project, to store work shifts for
    """
    project_name = StringEntityField(span=5)
    hourly_rate = IntEntityField()
    lead = ("skapa", "nytt")
    trail = ("projekt",)

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.create_new_project(message)


class SetProjectAsDefault(Intent):
    """
    Set a project as default; meaning it's implicitly selected if
    the project name is omitted when a workshift is created.
    """
    lead = ("projekt", "sätt")
    trail = ("default", "standard", "standardprojekt")
    project_name = StringEntityField(valid_strings=Project.all_project_names)

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.set_project_as_default(message)


class ActivateProject(Intent):
    """
    Activate a project in Jarvis
    """
    lead = ("aktivera",)
    trail = ("projekt",)
    project_name = StringEntityField(valid_strings=Project.all_project_names,
                                     span=5)

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.activate_project(message)


class DeactivateProject(Intent):
    """
    Deactivate a project in Jarvis
    """
    lead = ("avaktivera", "deaktivera", "pensionera", "inaktivera")
    trail = ("projekt",)
    project_name = StringEntityField(valid_strings=Project.all_project_names,
                                     span=5)

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.deactivate_project(message)


class ListProjects(Intent):
    """
    List all projects in Jarvis
    """
    lead = ("visa", "lista", "hämta")
    trail = ("projekt",)

    def respond(self, message: Message) -> Reply | ReplyStream:
        reply = ReplyStream()
        for project in Project.objects.all():
            description = (f"**Namn:** {project.name}\n"
                           f"**Arvode:** {project.hourly_rate} kr/h\n"
                           f"**Aktiv:** {'Ja' if project.is_active else 'Nej'}")
            reply.put(Reply(description))
        return reply

class ExportWorkShiftsToFile(Intent):
    """
    Export workshifts to an xlsx file.
    """
    exact_match = ("exportera", "arbetspass",)
    project_name = StringEntityField(valid_strings=Project.all_project_names)
    month = StringEntityField(valid_strings=Month.names_as_list())
    year = IntEntityField()

    def respond(self, message: Message) -> Reply | ReplyStream:
        project_name = message.entities["project_name"].lower()
        if (project := self.ability.get_project_by_name(project_name)) is None:
            return Reply("Projektet kunde inte hittas.")
        if project.is_active is False:
            return Reply("Projektet är inte aktivt - aktivera det först.")

        if (year := message.entities["year"]) is None:
            year = datetime.now(tz=app.settings.TIME_ZONE).year
        if (month_name := message.entities["month"]) is None:
            month = datetime.now(tz=app.settings.TIME_ZONE).month
        else:
            month = Month.get_month_calendar_int_from_name(month_name)

        if not (work_shifts_file := self.ability.export_work_shifts_to_file(
            project=project,
            year=year,
            month=month)
        ):
            return Reply("Har har inte antecknat några arbetpass med "
                         f"{project_name} i {month} {year}...")

        return Reply(f"Självklart, här är arbetspassen för {project.name} under "
                     f"{month} {year}! :smiley:",
                     file=work_shifts_file,
                     file_name=f"arbetspass_{project.name}_{year}_{month}.xlsx")
