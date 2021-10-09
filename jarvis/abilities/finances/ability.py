from typing import Union

import pymongo as pymongo
from pyttman import settings
from pyttman.core.ability import Ability
from pyttman.core.communication.models.containers import Reply, ReplyStream, Message
from pyttman.core.intent import Intent
from pyttman.core.parsing import identifiers
from pyttman.core.parsing.parsers import ValueParser

from jarvis.abilities.finances.utils import Expense


class AddExpense(Intent):
    """
    Allows users to add expenses.
    """
    lead = ("utgift", "expense", "köpt", "köpte", "bought")
    description = "Lägg till en utgift. Utgifter sparas personligt."
    example = "utgift mat 650"

    class EntityParser:
        expense_name = ValueParser(span=10)
        expense_value = ValueParser(identifier=identifiers.IntegerIdentifier)

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        expense_name = self.entities.get("expense_name")
        expense_value = self.entities.get("expense_value")

        if None in (expense_value, expense_name):
            return Reply("Du måste ange både namn och pris på vad du har köpt.")

        if (user_expenses := self.storage.get("expenses").get(message.author)) is None:
            user_expenses = []
            self.storage.get("expenses")[message.author] = user_expenses

        expense = Expense(price=expense_value, name=expense_name)
        user_expenses.append(expense)
        return Reply(f"Utgift sparad: '{expense.name}' {expense.price} kronor.")


class GetExpensesForUser(Intent):
    """
    Returns a ReplyStream of all expenses for the
    user making the request.
    """
    lead = ("visa", "lista", "show", "get")
    trail = ("utgifter", "expenses", "expense", "utlägg")

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        if expenses := self.storage.get("expenses").get(message.author):
            return ReplyStream(expenses)
        return Reply(f"Det finns inga lagrade utgifter för dig, {message.author}")


class FinanceAbility(Ability):
    intents = (AddExpense, GetExpensesForUser)
    mongo_db: pymongo.MongoClient = None

    def configure(self):
        self.mongo_db = pymongo.MongoClient()

        # Initialize an Expense dict mapping Users to their Expenses
        self.storage.put("expenses", {})
