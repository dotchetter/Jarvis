import pyttman
from pyttman.core.intent import Intent
from pyttman.core.containers import (
    Message,
    Reply,
    ReplyStream
)

from jarvis.models import User
from jarvis.abilities.finance.models import Expense


class DevInfo(Intent):
    """
    Returns info about the environment which Jarvis is running in.
    """
    lead = ("berätta",)
    trail = ("dig",)
    example = "Berätta om dig"
    description = "Visar information om mig, Jarvis!"

    def respond(self, message: Message) -> Reply:
        return Reply(f"Version: {pyttman.settings.APP_VERSION}\n"
                     f"db: {pyttman.settings.db_name}\n"
                     f"Scheduler threads: "
                     f"{len(list(pyttman.schedule.get_jobs()))}\n"
                     f"Pyttman version: {pyttman.__version__}\n"
                     f"Dev mode: {pyttman.settings.DEV_MODE}")


class UserInfo(Intent):
    """
    Returns info about the user writing the question
    """
    lead = ("berätta",)
    trail = ("mig",)
    example = "Berätta om mig"
    description = "Visar information för dig, som lagras i Jarvis!"

    def respond(self, message: Message) -> Reply | ReplyStream:
        if (user := User.objects.from_message(message)) is None:
            return Reply("Det finns ingen information om dig")

        expenses_for_user = Expense.objects.filter(user_reference=user).all()
        expenses_sum = expenses_for_user.sum('price')
        expenses_count = expenses_for_user.count()
        finance_info = f"Du har sparat **{expenses_count}** " \
                       f"utgifter totalt, till en totalsumma värd " \
                       f"**{expenses_sum}** kronor, inte dåligt!"

        aliases = ", ".join(user.aliases)
        alias_info = f"Kärt barn har **många namn!** Du har " \
                     f"{len(user.aliases)} alias, nämligen: {aliases}.\n"

        info = (f"**Här är lite info om dig:\n\n**",
                alias_info,
                finance_info)
        return ReplyStream(info)
