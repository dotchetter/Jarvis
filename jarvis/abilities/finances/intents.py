from datetime import datetime, timedelta
from typing import Union

from mongoengine import QuerySet
from pyttman.core.communication.models.containers import Message, Reply, ReplyStream
from pyttman.core.intent import Intent
from pyttman.core.parsing import identifiers
from pyttman.core.parsing.parsers import ValueParser, ChoiceParser

from jarvis.abilities.finances.models import Expense
from jarvis.abilities.finances.month import Month
from jarvis.abilities.finances.util import get_message_author_id


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

        expense = Expense(price=expense_value, name=expense_name, author=author_id)
        expense.save()

        return Reply(f"Utgift sparad-: '{expense.name}', pris: {expense.price}:-")


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

        :field sum_expenses:
            If this entity is parsed in a message, the user
            is not interested of the whole list of expenses
            but the sum for the current period (month).

        :field month:
            Users can ask for expenses / sum of expenses for
            a certain month, which is parsed in to this entity.

        :field user_id:
            Users can ask for expenses / sum of expenses for
            other users than themselves, which is parsed in to
            this entity.
        """
        sum_expenses = ChoiceParser(choices=("sum", "summa", "summera",
                                             "summerade", "summed", "totalt",
                                             "totala", "total"))
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
        date_format = "%y-%m-%d"
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
            user_id = int(self.entities.get("user_id"))
        except (ValueError, TypeError):
            # Parsed value could not typecast to int or is None
            user_id = message.author.id

        query_result: QuerySet = Expense.objects.filter(author=user_id,
                                                        created__gte=query_datetime_from,
                                                        created__lte=query_datetime_to)
        if not query_result:
            return Reply(self.storage["default_replies"]["no_expenses_matched"])

        # The user wanted a sum of their expenses
        if self.entities.get("sum_expenses"):
            return Reply(f"Summan för {query_month_name} "
                         f"är **{query_result.sum('price')}**:-")

        for expense in query_result:
            pretty_expenses.append(f":pinched_fingers: **{expense.name}**\n"
                                   f":money_with_wings: {expense.price}:-\n"
                                   f":calendar: **{expense.created.strftime(date_format)}**")
            pretty_expenses.append("-" * 20)
        return ReplyStream(pretty_expenses)


class CreateSplitBillsReportIntent(Intent):
    """
    # TODO - Write docstring
    """
    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        pass

