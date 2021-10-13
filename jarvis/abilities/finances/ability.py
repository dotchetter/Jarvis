from typing import Union

import mongoengine
import pymongo.errors
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

        expense = Expense(price=expense_value, name=expense_name, author=message.author.id)
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
            if author_expenses := Expense.objects(author=author_id):
                for expense in author_expenses:
                    pretty_expenses.append(f"* Namn: {expense.name}\n"
                                           f"  Pris: {expense.price}\n"
                                           f"  Datum: {expense.created}")
                    return ReplyStream(pretty_expenses)
        except pymongo.errors.ServerSelectionTimeoutError:
            return Reply("Ett fel uppstod när data hämtades. Prova en annan sökning.")
        return Reply(f"Det finns inga utgifter sparade för {message.author.mention}")


class FinanceAbility(Ability):
    intents = (AddExpense, GetExpenses)

    def configure(self):
        mongoengine.connect(settings.MONGO_ATLAS_URL)
