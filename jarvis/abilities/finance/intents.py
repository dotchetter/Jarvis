from datetime import datetime
from typing import Union, Collection

import pandas
import pyttman
from mongoengine import QuerySet, Q
from pyttman.core.containers import Message, Reply, ReplyStream
from pyttman.core.entity_parsing.fields import TextEntityField, \
    BoolEntityField, IntEntityField
from pyttman.core.intent import Intent

from jarvis.abilities.finance.helpers import SharedExpensesApp
from jarvis.abilities.finance.models import Expense, Debt
from jarvis.abilities.finance.month import Month
from jarvis.models import User
from jarvis.utils import extract_username


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

    expense_name = TextEntityField(span=10)
    store_for_next_month = BoolEntityField(message_contains=("nästa",
                                                             "månad"))
    expense_value = IntEntityField()
    store_for_username = TextEntityField(
        valid_strings=SharedExpensesApp.enrolled_usernames
    )

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

        if (user := User.objects.from_username_or_alias(
                store_for_username)) is None:
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

    sum_expenses = BoolEntityField(message_contains=("sum", "summa",
                                                     "summera",
                                                     "summerade",
                                                     "summed", "totalt",
                                                     "totala", "total"))
    show_most_recent_expense = BoolEntityField(message_contains=("senaste",))
    month = TextEntityField(valid_strings=tuple(i.name for i in Month))
    username_for_query = TextEntityField(
        valid_strings=SharedExpensesApp.enrolled_usernames
    )

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
            user = User.objects.from_username_or_alias(username_for_query)
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

    deduct_debts = BoolEntityField(message_contains=("skuld", "lån"))

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        reply_stream = ReplyStream()
        buckets = SharedExpensesApp.calculate_split()
        top_paying_bucket: SharedExpensesApp.SharedExpenseBucket = buckets.pop()
        top_paying_username = top_paying_bucket.user.username.capitalize()

        reply_stream.put(f"{top_paying_username} har betalat "
                         f"**{top_paying_bucket.paid_amount}:-** denna månad.")

        while buckets:
            current_bucket = buckets.pop()
            bucket_username = current_bucket.user.username.capitalize()

            if current_bucket.paid_amount == top_paying_bucket.paid_amount:
                msg = f"{bucket_username} har betalat lika mycket " \
                      f"som {top_paying_username}: **" \
                      f"{current_bucket.paid_amount}:-**, " \
                      f"ingen kompensation behövs."
            else:
                msg = f"{bucket_username} har betalat " \
                      f"**{current_bucket.paid_amount}:" \
                      f"-**, och ska kompensera {top_paying_username} med " \
                      f"**{current_bucket.compensation_amount}:-**."

            reply_stream.put(msg)

            if message.entities["deduct_debts"] is True:
                bucket_after_debts = SharedExpensesApp.calculate_debt_balance(
                    top_paying_bucket=top_paying_bucket,
                    comparison_bucket=current_bucket)

                msg = f"Med skulder inräknade blir " \
                      f"{bucket_username} skyldig {top_paying_username} " \
                      f"**{bucket_after_debts.compensation_amount}:-** " \
                      f"istället."
                reply_stream.put(msg)

        return reply_stream


class AddDebt(Intent):
    """
    Adds a Debt for a user. Who is borrower and lender is
    determined by the message contents.
    """
    example = "Jag har lånat 100 av Katrin"
    lead = ("lånat", "lånade", "borrowed", "borrow", "compensation_amount", "skyldig")

    amount = IntEntityField()
    lender = TextEntityField(valid_strings=SharedExpensesApp.enrolled_usernames)

    def respond(self, message: Message) -> Reply | ReplyStream:
        lender_name = extract_username(message, "lender")

        if (borrower := User.objects.from_message(message)) is None:
            return Reply(self.storage["default_replies"]["no_users_matches"])

        if (amount := message.entities.get("amount")) is None:
            return Reply("Du måste ange belopp på skulden")

        try:
            lender: User = User.objects.from_username_or_alias(lender_name)
        except (IndexError, ValueError):
            pyttman.logger.log(f"Lender not found for entity "
                               f"provided: '{lender_name}'")
            return Reply(self.storage["default_replies"]["no_users_matches"])

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

    borrower_name = TextEntityField(
        valid_strings=SharedExpensesApp.enrolled_usernames,
    )

    def respond(self, message: Message) -> Reply | ReplyStream:
        reply_stream = ReplyStream()
        debts_by_lender: dict[User, int] = {}
        borrower_name = extract_username(message, "borrower_name")
        borrower: User = User.objects.from_username_or_alias(borrower_name)
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
    Allows users to repay an outstanding compensation_amount to other users.
    """
    description = "Återbetalning av en skuld, eller en del av en skuld till " \
                  "en annan användare."
    example = "jag har betalat tillbaka 100:- till <användare>"
    lead = ("betalat", "betala", "återbetalat", "kompensera", "kompenserat")

    repaid_amount = IntEntityField()
    borrower_name = TextEntityField(
        valid_strings=SharedExpensesApp.enrolled_usernames
    )

    def respond(self, message: Message) -> Reply | ReplyStream:
        repaid_amount: int = message.entities.get("repaid_amount")
        borrower_name: str = message.entities.get("borrower_name")
        remaining_repaid_amount = repaid_amount
        lender = User.objects.from_message(message)

        try:
            borrower: User = User.objects.from_username_or_alias(borrower_name)
        except (IndexError, ValueError):
            pyttman.logger.log(f"Borrower not found for entity "
                               f"provided: '{borrower_name}'")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        if lender == borrower:
            return Reply("Endast lånegivaren kan registrera en inbetald "
                         "skuld.")

        borrower_capitalized = borrower.username.capitalize()
        lender_capitalized = lender.username.capitalize()

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

        # Looks like the user overpaid.
        # Create a new compensation_amount going the other way.
        if remaining_repaid_amount > 0:
            Debt.objects.create(amount=remaining_repaid_amount,
                                lender=borrower,
                                borrower=lender)
            reply = Reply(
                f"{borrower_capitalized} har överbetalat "
                f"dig med **{remaining_repaid_amount}:-**. En skuld "
                f"har skapats {borrower_capitalized} har lånat ut *"
                f"*{remaining_repaid_amount}**:- till "
                f"{lender_capitalized}.")
        else:
            reply = Reply(
                f"{borrower_capitalized} har minskat sin skuld till dig "
                f"med **{repaid_amount}**:-.")
        return reply
