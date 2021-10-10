from typing import Union

import mongoengine
from pyttman import settings
from pyttman.core.ability import Ability
from pyttman.core.communication.models.containers import Reply, ReplyStream, Message
from pyttman.core.intent import Intent
from pyttman.core.parsing import identifiers
from pyttman.core.parsing.parsers import ValueParser

from jarvis.models import Expense, Author


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

        if authors := Author.objects(name=message.author).all_fields():
            author = authors.first()
            print("This author is already in the database:", author)
        else:
            print("The author was not in the database; saving them")
            author = Author(name=message.author).save()

        expense = Expense(price=expense_value, name=expense_name, author=author)
        expense.save()

        return Reply(f"Utgift sparad: '{expense.name}', pris: {expense.price}:-")


class GetExpensesForUser(Intent):
    """
    Returns a ReplyStream of all expenses for the
    user making the request.
    """
    lead = ("visa", "lista", "show", "get")
    trail = ("utgifter", "expenses", "expense", "utlägg")

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        author_expenses = Expense.objects(author__name=message.author)
        return ReplyStream(f"Namn: {i.name}, pris: {i.price}" for i in author_expenses)


class FinanceAbility(Ability):
    intents = (AddExpense, GetExpensesForUser)

    def configure(self):
        mongoengine.connect(db="jarvis", username="db_full_access_user",
                            password=settings.MONGO_ATLAS_PW, host=settings.MONGO_ATLAS_URL)
