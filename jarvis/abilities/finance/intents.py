from datetime import datetime
from typing import Union, Any

import pandas
import pyttman
from mongoengine import QuerySet
from pyttman.core.communication.models.containers import Message, Reply, \
    ReplyStream
from pyttman.core.entity_parsing import identifiers
from pyttman.core.entity_parsing.fields import TextEntityField, \
    BoolEntityField, IntegerEntityField, EntityFieldBase
from pyttman.core.entity_parsing.identifiers import IntegerIdentifier, \
    CapitalizedIdentifier
from pyttman.core.intent import Intent

from jarvis.models import User
from jarvis.abilities.finance.helpers import SharedExpensesApp
from jarvis.abilities.finance.models import Expense, Debt
from jarvis.abilities.finance.month import Month


class CustomIntegerEntityField(EntityFieldBase):
    """
    IntegerEntityField classes specialize in finding numbers.
    The value output type from this EntityField is <int>.
    """
    type_cls = int
    identifier_cls = IntegerIdentifier

    @classmethod
    def perform_type_conversion(cls, value: str) -> Any:
        return cls.type_cls("".join(i for i in value if i.isdigit()))


class AddExpense(Intent):
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
        expense_name = TextEntityField(span=10)
        store_for_next_month = BoolEntityField(message_contains=("nästa",
                                                                 "månad"))
        expense_value = CustomIntegerEntityField()
        store_for_username = TextEntityField(prefixes=("for", "för",
                                                       "user", "användare"))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        expense_name = message.entities.get("expense_name")
        expense_value = message.entities.get("expense_value")
        for_next_month = message.entities.get("store_for_next_month")
        store_for_username = extract_username(message, "store_for_username")
        account_for_date = datetime.now()

        if None in (expense_value, expense_name):
            return Reply("Du måste ange både namn och "
                         "pris på vad du har köpt.")

        if for_next_month:
            account_for_date += pandas.DateOffset(months=1)

        try:
            user = User.get_by_alias_or_username(store_for_username).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"No db User matched: {store_for_username}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        Expense.objects.create(price=expense_value, expense_name=expense_name,
                               user_reference=user, created=datetime.now(),
                               account_for=account_for_date)

        return Reply(f"Utlägget sparades för {user.username.capitalize()}")


class GetExpenses(Intent):
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
        sum_expenses = BoolEntityField(message_contains=("sum", "summa",
                                                         "summera", "summerade",
                                                         "summed", "totalt",
                                                         "totala", "total"))
        show_most_recent_expense = BoolEntityField(message_contains=("senaste",))
        month = TextEntityField(valid_strings=tuple(i.name for i in Month))
        username_for_query = TextEntityField(prefixes=("for", "för", "user",
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
        username_for_query = extract_username(message, "username_for_query")

        try:
            user = User.get_by_alias_or_username(username_for_query).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"No db User matched: {username_for_query}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        try:
            month_for_query = message.entities.get("month")
        except AttributeError:
            month_for_query = None

        expenses: QuerySet = Expense.get_expenses_for_period_and_user(
            month_for_query=month_for_query,
            user=user)

        if message.entities.get("show_most_recent_expense") is True:
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


class AddDebt(Intent):
    """
    Adds a Debt for a user. Who is borrower and lender is
    determined by the message contents.
    """
    lead = ("lånat", "lånade", "borrowed", "lån", "borrow")

    class EntityParser:
        amount = CustomIntegerEntityField()
        borrower_name = TextEntityField(identifier=CapitalizedIdentifier)
        lender_name = TextEntityField(prefixes=("av", "från", "from", "by"))

    def respond(self, message: Message) -> Reply | ReplyStream:
        lender_name = message.entities.get("lender_name")
        borrower_name = extract_username(message, "borrower_name")
        account_for = datetime.now()

        if (amount := message.entities.get("amount")) is None:
            return Reply("Du måste ange belopp på skulden")

        try:
            borrower: User = User.get_by_alias_or_username(borrower_name).first()
        except (IndexError, ValueError):
            return Reply(self.storage["default_replies"]["no_users_matches"])

        try:
            lender: User = User.get_by_alias_or_username(lender_name).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"No db User matched: {lender_name}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        Debt.objects.create(borrower=borrower, lender=lender,
                            amount=amount, account_for=account_for)

        return Reply(f"Okej, jag har antecknat att "
                     f"{borrower.username.capitalize()} "
                     f"har lånat {amount}:- av "
                     f"{lender.username.capitalize()}.")


def extract_username(message: Message, entity_name: str) -> str:
    """
    Extracts the appropriate username depending on whether
        * it was mentioned in an Entity,
        * it's accessible on message.author.id (discord)
        * it's accessible on message.author (pyttman dev mode)
    """
    # Default to message.author.id unless provided as an entity
    if (username_for_query := message.entities.get(entity_name)) is None:
        try:
            username_for_query = message.author.id
        except AttributeError:
            username_for_query = message.author
    return str(username_for_query)
