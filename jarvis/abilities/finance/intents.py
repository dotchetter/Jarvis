from datetime import datetime
from typing import Union, Any

import pandas
import pyttman
from mongoengine import QuerySet
from pyttman.core.communication.models.containers import Message, Reply, \
    ReplyStream
from pyttman.core.intent import Intent
from pyttman.core.parsing import identifiers
from pyttman.core.parsing.parsers import ValueParser, ChoiceParser

from jarvis.abilities.finance.helpers import SharedExpensesApp
from jarvis.abilities.finance.month import Month
from jarvis.abilities.administrative.models import User
from jarvis.abilities.finance.models import Expense


class AddExpenseIntent(Intent):
    """
    Allows users to add expenses.
    """
    lead = ("spara", "ny", "nytt", "new", "save", "store")
    trail = ("utgift", "expense", "utlägg", "purchase")
    description = "Spara en ny utgift i Jarvis. Du kan ange " \
                  "ett namn på personen som har lagt ut pengar, " \
                  "om det inte är din egna utgift. Nämner du ingen " \
                  "annan sparas den automatiskt för dig. " \
                  "Om nuvarande månad redan är konterad, kan du " \
                  "spara utgiften för nästa månad. Ange då " \
                  "'nästa månad' i meddelandet, så hamnar utgiften " \
                  "för nästkommande period. Ange namnet på vad du " \
                  "har köpt och beloppet, endast heltal."
    example = "[Spara ett nytt utlägg för dig]: " \
              "nytt utlägg Matvaror för veckan 250\n" \
              "[Spara ett nytt utlägg för någon annan]: " \
              "spara utgift för Simon bensin 500\n" \
              "[Spara ett nytt utlägg för nästa period]: " \
              "Spara utgift nästa månad Kruka till växten 249"

    class EntityParser:
        expense_name = ValueParser(span=10)
        store_for_next_month = ChoiceParser(choices=("nästa", "månad"),
                                            multiple=True)
        expense_value = ValueParser(identifier=identifiers.IntegerIdentifier)
        username_for_query = ValueParser(prefixes=("for", "för",
                                                   "user", "användare"))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        expense_name = message.entities.get("expense_name")
        expense_value = message.entities.get("expense_value")
        for_next_month = bool(message.entities.get("store_for_next_month"))

        if None in (expense_value, expense_name):
            return Reply("Du måste ange både namn och "
                         "pris på vad du har köpt.")

        # If the user want to register this expense for the next
        # calendar month, add one month to the Expense.created field.
        account_for_date = datetime.now()

        if for_next_month:
            account_for_date += pandas.DateOffset(months=1)

        username_for_query = extract_username(message)

        try:
            user = User.get_by_alias_or_username(username_for_query).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"No db User matched: {username_for_query}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        Expense.objects.create(price=expense_value.value,
                               expense_name=expense_name.value,
                               user_reference=user,
                               created=datetime.now(),
                               account_for=account_for_date)

        return Reply(f"Utlägget sparades för {user.username.capitalize()}")


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
    trail = ("utgift", "utgifter", "expense",
             "expenses", "utlägg", "utgiften")
    description = "Hämta utgifter för dig, eller en annan person." \
                  "Om du vill visa utgifter för någon annan, kan du " \
                  "ange deras namn."
    example = "Visa utgifter för Simon"

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

        :field username_for_query:
            Users can ask for expenses / sum of expenses for
            other users than themselves, which is parsed in to
            this entity.
        """
        sum_expenses = ChoiceParser(choices=("sum", "summa", "summera",
                                             "summerade", "summed", "totalt",
                                             "totala", "total"))
        show_most_recent_expense = ChoiceParser(choices=("senaste",))
        month = ChoiceParser(choices=tuple(i.name for i in Month))
        username_for_query = ValueParser(prefixes=("for", "för", "user",
                                                   "användare"))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        """
        Isolate for which user the intent is for.
        If the sum is asked for, simply provide only the
        sum - otherwise return all expenses for the
        selected month.
        :param message:
        :return:
        """
        username_for_query = extract_username(message)

        try:
            user = User.get_by_alias_or_username(username_for_query).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"No db User matched: {username_for_query}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        try:
            month_for_query = message.entities.get("month").value
        except AttributeError:
            month_for_query = None

        expenses: QuerySet = Expense.get_expenses_for_period_and_user(
            month_for_query=month_for_query,
            user=user)

        if message.entities.get("show_most_recent_expense"):
            latest_expense = Expense.objects.filter(
                user_reference=user
            ).latest()
            return Reply(latest_expense)

        if not expenses:
            return Reply(self.storage["default_replies"]["no_expenses_matched"])

        # The user wanted a sum of their expenses
        month_name: str = Month(expenses.first().created.month).name.capitalize()

        if message.entities.get("sum_expenses"):
            expenses_sum = expenses.sum("price")

            return Reply(f"Summan för {user.username.capitalize()} "
                         f"i {month_name} är hittills: **{expenses_sum}**:-")

        return ReplyStream(expenses)


class CalculateSplitExpenses(Intent):
    """
    This intent sums up a month's expenses
    for all users who have contributed to the
    shared expenses, and splits it up evenly.
    """
    lead = ("kontera", "bokför", "beräkna", "splitta", "dela")
    trail = ("utgifter", "utlägg", "kostnader")
    example = "Kontera utgifter"
    description = "Beräkna ugfiter för alla användare för " \
                  "nuvarande period. I rapporten framgår " \
                  "om vissa har betalat mer, och hur mycket " \
                  "dessa ska kompenseras med för att alla " \
                  "ska ha betalat lika mycket."

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        buckets = SharedExpensesApp.calculate_split()
        top_paying = buckets.pop()
        output = [f"**{top_paying.user.username.capitalize()}** "
                  f"har betalat mest denna månad med en total av "
                  f"**{top_paying.paid_amount}:-** hittills.\n"]

        while buckets:
            bucket = buckets.pop()
            output.append(f"{bucket.user.username.capitalize()} har betalat "
                          f"**{bucket.paid_amount}:-**, och ska kompensera "
                          f"{top_paying.user.username.capitalize()} med "
                          f"**{bucket.debt}:-**.")

        return ReplyStream(output)


def extract_username(message: Message) -> str:
    """
    Extracts the appropriate username depending on whether
        * it was mentioned in an Entity,
        * it's accessible on message.author.id (discord)
        * it's accessible on message.author (pyttman dev mode)
    :param message:
    :return: str
    """
    # Default to message.author.id unless provided as an entity
    if (username_for_query := message.entities.get(
            "username_for_query")) is None:
        try:
            username_for_query = message.author.id
        except AttributeError:
            username_for_query = message.author
    else:
        username_for_query = username_for_query.value
    return str(username_for_query)
