import pyttman
from pyttman.core.communication.models.containers import Message, Reply
from pyttman.core.intent import Intent


class DevInfo(Intent):
    """
    Returns info about the environment which Jarvis is runnign in.
    """
    lead = ("berätta",)
    trail = ("dig",)

    def respond(self, message: Message) -> Reply:
        return Reply(f"Databas: {pyttman.settings.db_name}\n"
                     f"Scheduler threads: "
                     f"{len(list(pyttman.schedule.get_jobs()))}\n"
                     f"Pyttman version: {pyttman.__version__}\n"
                     f"Dev mode: {pyttman.settings.DEV_MODE}")

