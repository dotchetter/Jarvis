from datetime import datetime
from typing import Union, Collection

import pandas
import pyttman
from mongoengine import QuerySet, Q
from pyttman.core.containers import Message, Reply, ReplyStream
from pyttman.core.entity_parsing.fields import TextEntityField, \
    BoolEntityField, IntEntityField
from pyttman.core.entity_parsing.identifiers import CapitalizedIdentifier
from pyttman.core.intent import Intent

from jarvis.abilities.finance.helpers import SharedExpensesApp
from jarvis.abilities.finance.models import Expense, Debt
from jarvis.abilities.finance.month import Month
from jarvis.models import User
from jarvis.utils import extract_username, get_username_from_message


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
        expense_value = IntEntityField()
        store_for_username = TextEntityField(prefixes=("for", "för",
                                                       "user", "användare"))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        print(pyttman.app.settings)
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

        Expense.objects.create(price=expense_value,
                               expense_name=expense_name,
                               user_reference=user,
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
                                                         "summera",
                                                         "summerade",
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
        get_latest = message.entities["show_most_recent_expense"]

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

        if get_latest is True:
            latest_expense = Expense.objects.filter(
                user_reference=user
            ).latest()
            return Reply(latest_expense)

        if not expenses:
            return Reply(
                self.storage["default_replies"]["no_expenses_matched"])

        # The user wanted a sum of their expenses
        month_name: str = Month(
            expenses.first().created.month).name.capitalize()

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
    lead = ("kontera",)
    example = "Kontera utgifter"
    description = "Beräkna ugfiter för alla användare för " \
                  "nuvarande period. I rapporten framgår " \
                  "om vissa har betalat mer, och hur mycket " \
                  "dessa ska kompenseras med för att alla " \
                  "ska ha betalat lika mycket."

    class EntityParser:
        deduct_debts = BoolEntityField(message_contains=("skuld", "lån"))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        reply_stream = ReplyStream()
        buckets = SharedExpensesApp.calculate_split()
        top_paying_bucket: SharedExpensesApp.SharedExpenseBucket = buckets.pop()
        top_paying_username = top_paying_bucket.user.username.capitalize()

        reply_stream.put(f"{top_paying_username} har betalat "
                         f"**{top_paying_bucket.paid_amount}:-** denna månad.")

        while buckets:
            bucket = buckets.pop()
            bucket_username = bucket.user.username.capitalize()

            if bucket.paid_amount == top_paying_bucket.paid_amount:
                msg = f"{bucket_username} har betalat lika mycket " \
                      f"som {top_paying_username}: **" \
                      f"{bucket.paid_amount}:-**, ingen kompensation behövs."
            else:
                msg = f"{bucket_username} har betalat **{bucket.paid_amount}:" \
                      f"-**, och ska kompensera {top_paying_username} med " \
                      f"**{bucket.debt}:-**."
            reply_stream.put(msg)

            if message.entities["deduct_debts"] is True:
                # Find out if the top-paying user owes this user anything.
                top_paying_bucket_debt = Debt.objects.filter(
                    Q(borrower=top_paying_bucket.user) & Q(lender=bucket.user)
                ).sum("amount")

                # Don't output negative numbers.
                debt_if_refund = max(0, bucket.debt - top_paying_bucket_debt)
                reply_stream.put(
                    f"{top_paying_bucket.user.username.capitalize()} är skyldig "
                    f"{bucket.user.username.capitalize()} "
                    f"**{top_paying_bucket_debt}:-**. "
                    f"Om denna ska återbetalas i samband med "
                    f"konteringsersättningen, blir kompensationen istället "
                    f"**{debt_if_refund}**:-.")
        return reply_stream


class AddDebt(Intent):
    """
    Adds a Debt for a user. Who is borrower and lender is
    determined by the message contents.
    """
    example = "Simon lånade 100:- | " \
              "Katrin lånade 100 av Simon | " \
              "jag lånade ut 100 till Katrin | " \
              "Jag har lånat 100 av Katrin"
    lead = ("lånat", "lånade", "borrowed", "borrow", "debt", "skyldig")

    class EntityParser:
        amount = IntEntityField()

        borrower_third_person = TextEntityField(
            suffixes=("av", "från", "by"),
            valid_strings=SharedExpensesApp.enrolled_usernames)

        lender_third_person = TextEntityField(
            identifier=CapitalizedIdentifier,
            prefixes=("av",),
            valid_strings=SharedExpensesApp.enrolled_usernames)

        borrower_mentioned_alone = TextEntityField(
            valid_strings=SharedExpensesApp.enrolled_usernames)

    def respond(self, message: Message) -> Reply | ReplyStream:
        print(message.entities)
        user_is_lender = False
        amount = message.entities["amount"]
        borrower_third_person = message.entities["borrower_third_person"]
        lender_third_person = message.entities["lender_third_person"]
        borrower_mentioned_alone = message.entities["borrower_mentioned_alone"]

        if amount is None:
            return Reply("Du måste ange vem du lånat av, "
                         "eller vem du lånat ut pengar till.")

        if borrower_mentioned_alone and not any((borrower_third_person,
                                                 lender_third_person)):
            # The current user is the lender, implicitly.
            user_is_lender = True
            lender_name = get_username_from_message(message)
            borrower_name = extract_username(message,
                                             "borrower_mentioned_alone")
        elif borrower_third_person and lender_third_person:
            # Lender and borrower declared explicitly
            borrower_name = extract_username(message, "borrower_third_person")
            lender_name = extract_username(message, "lender_third_person")
        elif lender_third_person and not any((borrower_third_person,
                                             borrower_mentioned_alone)):
            # Lender mentioned explicitly, borrower is current user implicitly
            borrower_name = get_username_from_message(message)
            lender_name = extract_username(message, "lender_third_person")
        else:
            return Reply("Jag förstod inte vem som lånat av vem.. försök "
                         "igen. Du kan alltid be om hjälp för att se exempel.")

        if (amount := message.entities.get("amount")) is None:
            return Reply("Du måste ange belopp på skulden")

        try:
            borrower: User = User.get_by_alias_or_username(
                borrower_name).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"Borrower not found for entity "
                               f"provided: '{borrower_name}'")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        try:
            lender: User = User.get_by_alias_or_username(lender_name).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"Lender not found for entity "
                               f"provided: '{lender_name}'")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        if borrower == lender and user_is_lender:
            return Reply("Glöm inte att ange vem du lånade pengar från.")

        Debt.objects.create(borrower=borrower, lender=lender, amount=amount)

        return Reply(f"Okej, jag har antecknat att "
                     f"{borrower.username.capitalize()} "
                     f"har lånat {amount}:- av "
                     f"{lender.username.capitalize()}.")


class GetDebts(Intent):
    """
    Returns the sum of the debts registered for a borrower to
    a particular lender.
    """
    lead = ("visa", "lista", "show", "get", "hämta")
    trail = ("skuld", "skulder", "debts", "lån", "lånat", "lånade")

    class EntityParser:
        borrower_name = TextEntityField(identifier=CapitalizedIdentifier)

    def respond(self, message: Message) -> Reply | ReplyStream:
        reply_stream = ReplyStream()
        debts_by_lender: dict[User, int] = {}
        borrower_name = extract_username(message, "borrower_name")
        borrower: User = User.get_by_alias_or_username(borrower_name).first()
        debt_sum = Debt.objects.filter(borrower=borrower).sum("amount")

        if debt_sum == 0:
            return Reply(
                f"{borrower.username.capitalize()} "
                f"har inga skulder! :sunglasses:")
        else:
            reply_stream.put(
                f"**{borrower.username.capitalize()} har totalt {debt_sum}:- "
                f"i skulder registrerade, se nedan:**")

        for debt in Debt.objects.filter(borrower=borrower):
            try:
                debts_by_lender[debt.lender] += debt.amount
            except KeyError:
                debts_by_lender[debt.lender] = debt.amount

        for lender, _sum in debts_by_lender.items():
            debt = Debt(lender=lender, borrower=borrower, amount=_sum)
            reply_stream.put(debt)

        return reply_stream


class RepayDebt(Intent):
    """
    Allows users to repay an outstanding debt to other users.
    """
    description = "Återbetalning av en skuld, eller en del av en skuld till " \
                  "en annan användare."
    example = "jag har betalat tillbaka 100:- till <användare>"
    lead = ("betalat", "betala", "återbetalat", "kompensera", "kompenserat")

    class EntityParser:
        lender_name = TextEntityField(identifier=CapitalizedIdentifier)
        repaid_amount = IntEntityField()

    def respond(self, message: Message) -> Reply | ReplyStream:
        repaid_amount: int = message.entities.get("repaid_amount")
        lender_name: str = message.entities.get("lender_name")
        remaining_repaid_amount = repaid_amount
        current_user_username = get_username_from_message(message)

        try:
            lender: User = User.get_by_alias_or_username(lender_name).first()
        except (IndexError, ValueError):
            pyttman.logger.log(f"Lender not found for entity "
                               f"provided: '{lender_name}'")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        borrower: User = User.get_by_alias_or_username(
            current_user_username
        ).first()

        # Get debts common to this borrower and lender
        # Order the debts by amount, desc
        debts: Collection[Debt] = Debt.objects.filter(
            Q(borrower=borrower) & Q(lender=lender)
        ).order_by(
            "amount")

        for debt in debts:
            if remaining_repaid_amount <= 0:
                break
            debt_amount_before_reduce = debt.amount
            debt.amount -= remaining_repaid_amount
            remaining_repaid_amount -= debt_amount_before_reduce
            debt.delete() if debt.amount <= 0 else debt.save()

        # Looks like the user overpaid. Create a new debt going the other way.
        if remaining_repaid_amount > 0:
            Debt.objects.create(amount=remaining_repaid_amount,
                                lender=borrower,
                                borrower=lender)
            reply = Reply(
                f"Du har överbetalat {lender.username.capitalize()} med "
                f"**{remaining_repaid_amount}:-**. En skuld har skapats "
                f"där du lånat ut **{remaining_repaid_amount}**:- till "
                f"{lender.username.capitalize()}.")
        else:
            reply = Reply(
                f"Du har minskat din skuld till **"
                f"{lender.username.capitalize()}** med **"
                f"{repaid_amount}**:-.")
        return reply
