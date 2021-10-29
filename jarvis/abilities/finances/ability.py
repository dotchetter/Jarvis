import sys
from datetime import datetime, timedelta
from typing import Union

import mongoengine
from pyttman import settings
from pyttman.core.ability import Ability
from pyttman.core.communication.models.containers import Reply, ReplyStream, Message
from pyttman.core.intent import Intent
from pyttman.core.parsing import identifiers
from pyttman.core.parsing.parsers import ValueParser, ChoiceParser

from jarvis.abilities.finances.month import Month
from jarvis.abilities.finances.util import get_message_author_id
from jarvis.abilities.finances.models import Expense


class AddExpenseIntent(Intent):
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

        expense = Expense.objects.create(price=expense_value, name=expense_name, author=author_id)
        expense.save()

        return Reply(f"Okej, jag har antecknat det :slight_smile:")


class GetExpensesIntent(Intent):
    """
    Returns a ReplyStream of all expenses for the
    user making the request.

    If the user does not provide a name for someone
    else which they would like to see their expenses
    for; the query is performed on their name by
    message.author.name.
    """
    lead = ("visa", "lista", "show", "get", "hämta")
    trail = ("utgift", "utgifter", "expense", "expenses", "utlägg")
    description = "Hämta utgifter för dig, eller en annan person." \
                  "Om du vill visa utgifter för någon annan, tagga " \
                  "dem med '@'."
    example = "Visa utgifter för @Simon"

    class EntityParser:
        """
        Provide users the ability to get the sum of their expenses,
        and for which month the query is for.
        """
        sum_expenses = ChoiceParser(choices=("sum", "summa", "summera", "summerade",
                                             "summed", "totalt", "totala", "total"))
        month = ChoiceParser(choices=tuple(i.name for i in Month))
        user_id = ValueParser(prefixes=("for", "för"))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        """
        Isolate for which user the intent is for.
        If the sum is asked for, simply provide only the
        sum - otherwise return all expenses for the
        selected month.
        :param message:
        :return:
        """
        pretty_expenses = []

        # Use the provided month from entities if provided - or default to current month.
        query_year = datetime.now().year

        try:
            query_month: int = Month[self.entities["month"]].value
        except KeyError:
            query_month: int = datetime.now().month

        # Filter the query on the selected month, of current year
        query_month_name = Month(query_month).name
        query_datetime_from = datetime(year=query_year, month=query_month, day=1)
        query_datetime_to = datetime(year=query_year, month=query_month + 1, day=1)
        query_datetime_to -= timedelta(days=1)

        # Default to message.author.id unless provided as an entity
        try:
            if not (user_id := int(self.entities.get("user_id"))):
                raise ValueError
            else:
                user_id = int(user_id)
        except (ValueError, TypeError):
            user_id = message.author.id

        result = Expense.objects.filter(author=user_id,
                                       created__gte=query_datetime_from,
                                       created__lte=query_datetime_to)

        if not result:
            return Reply(self.storage["default_replies"]["no_expenses_matched_criteria"])

        # The user wanted a sum of their expenses
        if self.entities.get("sum_expenses"):
            return Reply(f"Summan för {query_month_name} är **{result.sum('price')}**:-")

        for expense in result:
            pretty_expenses.append(f":pinched_fingers: **{expense.name}**\n"
                                   f":money_with_wings: {expense.price}:-\n"
                                   f":calendar: **{expense.created.strftime('%y-%m-%d')}**")
            pretty_expenses.append("-" * 20)
        return ReplyStream(pretty_expenses)


class CreateSplitBillsReport(Intent):
    """
    # TODO - Write docstring
    """
    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        pass

    def test(self, my_list: list[str, int]) -> None:
        print(my_list)
        return None


class FinanceAbility(Ability):
    """
    This Ability class holds private-finance related
    Intents in Jarvis.

    Jarvis helps us collect and keep track of our
    expenses at home, to make splitting bills fair
    and square.
    """
    intents = (AddExpenseIntent, GetExpensesIntent)

    def configure(self):
        # Connect to the MongoDB Atlas database
        if settings.DEV_MODE:
            settings.MONGO_DB_CONFIG["db"] = settings.DB_NAME_DEV
        else:
            settings.MONGO_DB_CONFIG["db"] = settings.DB_NAME_PROD

        mongoengine.connect(**settings.MONGO_DB_CONFIG)

        # Set up a default reply when no expenses are found
        self.storage.put("default_replies",
                         {"no_expenses_matched_criteria": "Det finns inga utgifter "
                                                          "sparade med angivna kriterier"})

        if settings.INTERACTIVE_SHELL is True:
            import IPython
            IPython.embed()
            sys.exit(0)
