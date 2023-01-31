from datetime import datetime
from typing import Collection

import pandas
import pyttman
from dateutil.relativedelta import relativedelta
from mongoengine import QuerySet
from pyttman.core.ability import Ability
from pyttman.core.containers import Message, ReplyStream, Reply

from jarvis.abilities.finance.calculator import SharedFinancesCalculator
from jarvis.abilities.finance.intents import (
    AddExpense,
    GetExpenses,
    CalculateSplitExpenses,
    AddDebt,
    GetDebts,
    RepayDebt,
    UndoLastClosingCalculatedExpense,
    EnterMonthlyIncome,)
from jarvis.abilities.finance.models import Debt, AccountingEntry, Expense
from jarvis.abilities.finance.month import Month
from jarvis.models import User
from jarvis.utils import extract_username


class FinanceAbility(Ability):
    """
    This Ability class holds private-finance related
    Intents in Jarvis.

    Jarvis helps us collect and keep track of our
    expenses at home, to make splitting bills fair
    and square.
    """
    intents = (AddExpense,
               GetExpenses,
               CalculateSplitExpenses,
               AddDebt,
               GetDebts,
               RepayDebt,
               UndoLastClosingCalculatedExpense,
               EnterMonthlyIncome,)

    def before_create(self) -> None:
        """
        Configure hook method, executed before the app starts
        :return: None
        """

        # Set up a default reply when no expenses are found
        self.storage.put("default_replies",
                         {"no_expenses_matched": "Det finns inga utgifter "
                                                 "sparade med angivna "
                                                 "kriterier",
                          "no_users_matches":    "Jag hittade ingen "
                                                 "användare som matchade. "
                                                 "Om du angav ett namn, "
                                                 "kontrollera stavningen. "
                                                 "Om du inte angav något, "
                                                 "kontrollera att du är "
                                                 "registrerad."})

    def add_expense(self, message: Message):
        """
        Add a shared expense.
        """
        stream = ReplyStream()
        now = account_for_date = datetime.now()
        expense_name = message.entities.get("expense_name")
        expense_value = message.entities.get("expense_value")
        for_next_month = message.entities.get("store_for_next_month")
        store_for_username = extract_username(message, "store_for_username")
        current_month_start = now - relativedelta(day=1, hour=0, minute=0)
        current_month_end = now + relativedelta(day=31, hour=23, minute=59)
        accounting_entry_for_month = AccountingEntry.objects.filter(
            created__gte=current_month_start,
            created__lte=current_month_end)

        if None in (expense_value, expense_name):
            return Reply("Du måste ange både namn och "
                         "pris på vad du har köpt.")

        if for_next_month or accounting_entry_for_month:
            account_for_date += pandas.DateOffset(months=1)
            account_for_date = account_for_date.replace(day=1)

        if (user := User.objects.from_username_or_alias(
                store_for_username)) is None:
            pyttman.logger.log(f"No db User matched: {store_for_username}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        Expense.objects.create(price=expense_value,
                               expense_name=expense_name,
                               user_reference=user,
                               account_for=account_for_date)

        stream.put(f"Utgiften sparades för {user.username.capitalize()}. ")

        if for_next_month:
            stream.put("Utlägget har sparats för nästa månad.")
        elif accounting_entry_for_month:
            stream.put("Eftersom denna månad har konterats redan, har "
                       "utlägget sparats för nästa månad automatiskt.")
        return stream

    def get_expenses(self, message: Message):
        """
        Return expenses for a user, all in one reply stream
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

    @classmethod
    def register_debt(cls, message: Message) -> str:
        """
        Register debts between two users in the application.
        """
        author_is_borrower = message.entities["author_is_borrower"]
        author_is_lender = message.entities["author_is_lender"]
        amount = message.entities["amount"]

        if author_is_lender:
            # author_is_lender supersedes author_is_borrower
            lender = User.objects.from_message(message)
            borrower = extract_username(message, "other_person")
            borrower = User.objects.from_username_or_alias(borrower)
        elif author_is_borrower:
            borrower = User.objects.from_message(message)
            lender = extract_username(message, "other_person")
            lender = User.objects.from_username_or_alias(lender)
        else:
            lender = User.objects.from_message(message)
            borrower = extract_username(message, "other_person")
            borrower = User.objects.from_username_or_alias(borrower)
            author_is_lender = True

        if borrower == lender:
            return "Jag förstår inte vem som lånat av vem? " \
                   "Försök igen :slight_smile:"

        # Create the debt entry
        Debt.objects.create(borrower=borrower, lender=lender, amount=amount)
        total_debt_balance = Debt.objects.filter(
            borrower=borrower, lender=lender
        ).sum("amount")

        borrower_username = borrower.username.capitalize()
        lender_username = lender.username.capitalize()

        if author_is_lender:
            output = f"Jag har registrerat att du har lånat ut {amount}:- " \
                     f"till {borrower_username}."
        else:
            output = f"Jag har registrerat att du har lånat {amount}:- " \
                     f"av {lender_username}."
        if total_debt_balance:
            output += f"\n{borrower_username} har nu lånat " \
                      f"{total_debt_balance}:- av {lender_username} " \
                      f"({lender_username}s skulder till " \
                      f"{borrower_username} är ej avräknade)."
        return output

    @classmethod
    def get_debts(cls, message: Message) -> ReplyStream[str]:
        """
        Get debts for users
        """
        reply_stream = ReplyStream()
        debts_by_lender: dict[User, int] = {}
        borrower_name = extract_username(message, "borrower_name")
        borrower: User = User.objects.from_username_or_alias(borrower_name)
        debt_sum = Debt.objects.filter(borrower=borrower).sum("amount")

        if borrower is None:
            reply_stream.put("Hm, jag hittade inte personen som frågan gällde?")
            return reply_stream

        if debt_sum == 0:
            reply_stream.put(f"{borrower.username.capitalize()} "
                             f"har inga skulder! :sunglasses:")
            return reply_stream
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

    def repay_debt(self, message: Message):
        """
        One user pays back another user, an amount of money.
        """
        remaining_repaid_amount = repaid_amount = message.entities.get(
            "repaid_amount")
        author_is_borrower = message.entities.get("author_is_borrower")
        mentioned_user = message.entities.get("mentioned_user")
        author_user = User.objects.from_message(message)

        try:
            mentioned_user = User.objects.from_username_or_alias(mentioned_user)
        except (IndexError, ValueError):
            pyttman.logger.log(f"User not found for entity "
                               f"provided: '{mentioned_user}'")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        if author_is_borrower:
            lender = mentioned_user
            borrower = author_user
        else:
            lender = author_user
            borrower = mentioned_user

        borrower_capitalized = borrower.username.capitalize()
        lender_capitalized = lender.username.capitalize()

        # Get debts common to this borrower and lender
        # Order the debts by amount, desc
        debts: Collection[Debt] = Debt.objects.filter(
            borrower=borrower,
            lender=lender
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
            total_debt_balance = Debt.objects.filter(
                borrower=borrower, lender=lender
            ).sum("amount")
            reply = Reply(f"{borrower_capitalized} har "
                          f"minskat sin skuld till {lender_capitalized} "
                          f"med **{repaid_amount}**:-, och är nu skyldig "
                          f"{total_debt_balance}:-")
        return reply

    @staticmethod
    def calculate_split_expenses(message):
        """
        Perform an accounting entry, splitting expenses and create a balance
        sheet for users involved in the shared expenses' calculation.
        """
        calculator = SharedFinancesCalculator()
        participant_users = calculator.get_enrolled_users()
        try:
            calculations = calculator.calculate_split(
                participant_users=participant_users,
                month_for_query=message.entities["month"])
        except ValueError:
            return Reply("Åtminstone en användare har inte angivit månadsinkomst.")

        reply_stream = ReplyStream()
        accounting_entry = AccountingEntry()
        dt_fmt = pyttman.app.settings.DATETIME_FORMAT
        reply_stream.put(f"Konteringsunderlag: {datetime.now().strftime(dt_fmt)}")

        while calculations:
            calculation = calculations.pop()
            username = calculation.user.username.capitalize()
            accounting_entry.participants.append(calculation.user)

            msg = f"**{username}**:\n"
            msg += f"{username} har betalat {calculation.paid_amount:.2f}:- " \
                   f"denna period vilket utgör {calculation.quota_of_total * 100:.2f}% av " \
                   f"det totala beloppet {calculator.total_expense_sum:.2f}:-.\n"
            msg += f"{username} har en månadslön som motsvarar " \
                   f"{calculation.income_quotient * 100:.2f}:- av den " \
                   f"totala inkomsten av deltagarna.\n"

            if calculation.ingoing_compensation:
                msg += f"{username} har överbetalat sin del och ska bli kompenserad " \
                       f"med {calculation.ingoing_compensation:.2f}:- från övriga " \
                       f"deltagare."
            elif calculation.outgoing_compensation:
                msg += f"{username} har inte betalat sin del och ska kompensera " \
                       f"övriga deltagare med {calculation.outgoing_compensation:.2f}:- "
            else:
                msg += f"{username} har betalat exakt sin kvot och ska varken " \
                       f"kompenseras eller kompensera andra."

            reply_stream.put(msg)

            accounting_entry.accounting_result = msg
            if message.entities["close_current_period"]:
                accounting_entry.save()
                reply_stream.put("Innevarande månad har stängts. Nya utgifter "
                                 "som matas in under resten av denna månad "
                                 "kommer bokföras för nästa månad automatiskt.")
        return reply_stream

    @classmethod
    def delete_last_created_account_entry(cls) -> None:
        """
        Deletes the most-recent accounting entry object.
        """
        if last_entry := AccountingEntry.objects.order_by("-created").first():
            last_entry.delete()
            return last_entry
        return None
