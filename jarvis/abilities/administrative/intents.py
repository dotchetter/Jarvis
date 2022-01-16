import pyttman
from pyttman.core.communication.models.containers import Message, Reply
from pyttman.core.intent import Intent


class DBInfo(Intent):
    """
    Returns info about the database being used.
    """
    lead = ("vilken", "which")
    trail = ("databas", "db")

    def respond(self, message: Message) -> Reply:
        return Reply(pyttman.settings.db_name)
