from pyttman.core.containers import ReplyStream, Reply, Message
from pyttman.core.entity_parsing.fields import BoolEntityField, \
    StringEntityField, IntEntityField
from pyttman.core.entity_parsing.identifiers import DateTimeStringIdentifier
from pyttman.core.intent import Intent

from jarvis.abilities.timekeeper.models import WorkShift, Project
from jarvis.custom_identifiers import TimeStampIdentifier
from jarvis.models import User


class CreateWorkShift(Intent):
    """
    Starts a WorkShift or an Intermission.
    """
    lead = ("starta", "börja", "börjar", "påbörja", "ta", "tagit", "tar")
    trail = ("arbetspass", "pass", "skift", "jobb", "jobba", "arbeta")
    project_name = StringEntityField(valid_strings=Project.all_project_names)

    def respond(self, message: Message) -> Reply | ReplyStream:
        project_name = message.entities["project_name"]

        if (current_user := User.objects.from_message(message)) is None:
            return Reply("Jag vet inte vem frågan gäller?")
        if complaint := self.complain_if_workshift_exists(current_user):
            return complaint
        if (project := Project.objects.get_by_name_or_default_project(
                project_name)) is None:
            return self.ability.complain_no_project_was_chosen()

        WorkShift.objects.create(user=current_user, project=project).start()
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
    lead = ("avsluta", "stanna", "sluta", "slutar",
            "stopp", "stoppa", "ta", "tagit", "tar")
    trail = ("arbetspass", "pass", "skift", "jobb", "jobba",
             "arbeta", "rast", "paus", "lunch", "vila", "rasten",
             "jag")

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
        return self.ability.save_workshift_from_string(message)


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

