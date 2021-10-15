from typing import Union

import mongoengine
import pymongo.errors
import pyttman
from pyttman import settings
from pyttman.core.ability import Ability
from pyttman.core.communication.models.containers import Reply, ReplyStream, Message
from pyttman.core.intent import Intent
from pyttman.core.parsing import identifiers
from pyttman.core.parsing.identifiers import CapitalizedIdentifier
from pyttman.core.parsing.parsers import ValueParser

from jarvis.models import Expense


class AddExpense(Intent):
    """
    Allows users to add expenses.
    """
    lead = ("utgift", "expense", "köpt", "köpte", "bought")
    description = "Lägg till en utgift. Utgifter sparas personligt."
    example = "utgift frukost till imorgon 234"

    class EntityParser:
        expense_name = ValueParser(span=10)
        expense_value = ValueParser(identifier=identifiers.IntegerIdentifier)

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        expense_name = self.entities.get("expense_name")
        expense_value = self.entities.get("expense_value")

        if None in (expense_value, expense_name):
            return Reply("Du måste ange både namn och pris på vad du har köpt.")

        if settings.DEV_MODE:
            author_id = message.author
        elif message.mentions:
            author_id = message.mentions.pop().id
        else:
            author_id = message.author.id

        expense = Expense(price=expense_value, name=expense_name, author=author_id)
        expense.save()

        return Reply(f"Utgift sparad: '{expense.name}', pris: {expense.price}:-")


class GetExpenses(Intent):
    """
    Returns a ReplyStream of all expenses for the
    user making the request.

    If the user does not provide a name for someone
    else which they would like to see their expenses
    for; the query is performed on their name by
    message.author.name.
    """
    lead = ("visa", "lista", "show", "get")
    trail = ("utgifter", "expenses", "expense", "utlägg")

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        pretty_expenses = []

        # Perform the query on the mentioned user, if present, else the author
        if message.mentions:
            author_id = message.mentions.pop().id
        else:
            author_id = message.author.id

        try:
            for expense in Expense.objects(author=author_id):
                pretty_expenses.append(f"**Namn:** {expense.name}\n"
                                       f"**Belopp:** {expense.price}:-\n"
                                       f"**Datum:** {expense.created.strftime('%y-%m-%d %H:%M')}")
                pretty_expenses.append("\n")
        except pymongo.errors.ServerSelectionTimeoutError:
            return Reply("Ett fel uppstod när data hämtades. "
                         "Prova en annan sökning.")

        if len(pretty_expenses):
            return ReplyStream(pretty_expenses)
        return Reply(f"Det finns inga utgifter sparade för den personen.")


class FinanceAbility(Ability):
    intents = (AddExpense, GetExpenses)

    def configure(self):
        mongoengine.connect(**settings.MONGO_DB_CONFIG)
        print(Expense.objects(author=344940052268449792))