import datetime
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
from pyttman.core.parsing.parsers import ValueParser, ChoiceParser

from jarvis.abilities.finances.month import Month
from jarvis.models import Expense


class AddExpense(Intent):
    """
    Allows users to add expenses.
    """
    lead = ("spara", "ny", "nytt", "new", "save", "store")
    trail = ("utgift", "expense", "utlägg", "purchase")
    description = "Lägg till en utgift. Utgifter sparas personligt." \
                  "Du kan lägga till ett datum om köpet redan har skett " \
                  "- annars bokförs utlägget i dagens datum."
    example = "köpt varor för veckan 250 kronor"

    class EntityParser:
        expense_name = ValueParser(span=10)
        expense_value = ValueParser(identifier=identifiers.IntegerIdentifier)

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        expense_name = self.entities.get("expense_name")
        expense_value = self.entities.get("expense_value")
        author_id = get_message_author_id(message)

        # If authors entered a date in the expense, try and store it in the database
        if None in (expense_value, expense_name):
            return Reply("Du måste ange både namn och pris på vad du har köpt.")

        expense = Expense(price=expense_value, name=expense_name, author=author_id)
        expense.save()

        return Reply(f"Utgift sparad-: '{expense.name}', pris: {expense.price}:-")


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
    description = "Hämta utgifter för dig, eller en annan person." \
                  "Om du vill visa utgifter för någon annan, tagga " \
                  "dem med '@'."
    example = "Visa utgifter för @Simon"

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        pretty_expenses = []
        author_id = get_message_author_id(message)

        try:
            for expense in Expense.objects(author=author_id):
                pretty_expenses.append(f":pinched_fingers: **{expense.name}**\n"
                                       f":money_with_wings: {expense.price}:-\n"
                                       f":calendar: **{expense.created.strftime('%y-%m-%d')}**")
                pretty_expenses.append("=" * 20)
        except pymongo.errors.ServerSelectionTimeoutError:
            return Reply("Ett fel uppstod när data hämtades. "
                         "Prova en annan sökning.")

        if len(pretty_expenses):
            return ReplyStream(pretty_expenses)
        return Reply(f"Det finns inga utgifter sparade för den personen.")


class GetExpenseSum(Intent):
    """
    Returns the sum of all expenses for the author.
    """
    description = "Visa summan för dig denna månad."
    example = "Summera utlägg"
    lead = ("summera", "sum", "summa")
    trail = ("utlägg", "expenses", "purchase",
             "purchases", "utgift", "utgifter")

    class EntityParser:
        month = ChoiceParser(choices=tuple(i.name for i in Month))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:

        try:
            current_month: int = Month[self.entities["month"]].value
        except KeyError:
            current_month: int = datetime.datetime.now().month

        author_id = get_message_author_id(message)

        if not (expenses_for_author := Expense.objects(author=author_id)):
            return Reply("Det finns inga utgifter sparade för den användaren")

        filtered = [i.price for i in expenses_for_author if i.created.month == current_month]
        return Reply(f"Summan för {Month(current_month).name} är **{sum(filtered)}**:-")


class FinanceAbility(Ability):
    """
    This Ability class holds private-finance related
    Intents in Jarvis.

    Jarvis helps us collect and keep track of our
    expenses at home, to make splitting bills fair
    and square.
    """
    intents = (AddExpense, GetExpenses, GetExpenseSum)

    def configure(self):
        # Connect to the MongoDB Atlas database
        mongoengine.connect(**settings.MONGO_DB_CONFIG)


def get_message_author_id(message: Message) -> str:
    """
    Helper function until Pyttman provides the .author
    attribute as an Author object, platform independent.

    :param message: Pyttman Message to parse
    :return: str
    """
    # Perform the query on the mentioned user, if present, else the author
    try:
        if message.mentions:
            author_id = message.mentions.pop().id
        else:
            author_id = message.author.id
    except AttributeError:
        author_id = message.author
    return author_id
