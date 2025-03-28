from datetime import datetime
from typing import Collection

import pyttman
from pyttman.core.ability import Ability
from pyttman.core.containers import Message, ReplyStream, Reply

from jarvis.abilities.finance.calculator import SharedFinancesCalculator
from jarvis.abilities.finance import intents
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
    intents = (intents.AddExpense,
               intents.GetExpenses,
               intents.CalculateSplitExpenses,
               intents.AddDebt,
               intents.GetDebts,
               intents.RepayDebt,
               intents.UndoLastClosingCalculatedExpense,
               intents.EnterMonthlyIncome,
               intents.UndoLastExpense)

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
                          "no_users_matches": "Jag hittade ingen "
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
        expense_name = message.entities.get("expense_name")
        expense_value = message.entities.get("expense_value")
        store_for_username = extract_username(message, "store_for_username")
        recurring = message.entities.get("recurring")
        private = message.entities.get("private")



        if not expense_value and expense_name:
            return Reply("Du måste ange både namn och "
                         "pris på vad du har köpt.")

        if (user := User.objects.from_username_or_alias(
                store_for_username)) is None:
            pyttman.logger.log(f"No db User matched: {store_for_username}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        expense = Expense.objects.create(price=expense_value,
                                         expense_name=expense_name,
                                         user_reference=user,
                                         recurring_monthly=recurring,
                                         shared=not private)

        stream.put(f"Utgiften sparades för {user.username.capitalize()}.")
        if recurring:
            stream.put("Utgiften är markerad som återkommande.")
        if private:
            stream.put("Den har bokförts som en privat utgift bara för dig.")

        stream.put(expense)
        calculator = SharedFinancesCalculator()
        enrolled_users = calculator.get_enrolled_users()

        household_income = sum(user.profile.gross_income
                               for user in enrolled_users)
        expense_sum = calculator.calculate_split(
            participant_users=calculator.get_enrolled_users(),
            range_start=self._get_last_accounting_entry_datetime()
        ).pop().paid_amount

        budget_amount_left = max(0, int(household_income - expense_sum))
        stream.put(f"Ni har {budget_amount_left}:- kvar av er inkomst för denna period.")
        return stream

    def get_expenses(self, message: Message):
        """
        Return expenses for a user, all in one reply stream
        """
        username_for_query = extract_username(message, "username_for_query")
        get_latest = message.entities["show_most_recent_expense"]
        last_accounting_entry_date = self._get_last_accounting_entry_datetime()
        recurring_expenses_only = message.entities["recurring_expenses_only"]
        shared_only = message.entities["shared_only"]
        private_only = message.entities["private_only"]
        stream = ReplyStream()

        if shared_only and private_only:
            return Reply("Du kan inte välja både delade och privata utgifter samtidigt.")
        if shared_only:
            stream.put("Visar endast delade utgifter.")
        if private_only:
            stream.put("Visar endast privata utgifter.")

        try:
            user = User.objects.from_username_or_alias(username_for_query)
        except (IndexError, ValueError):
            pyttman.logger.log(f"No db User matched: {username_for_query}")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        if get_latest:
            return Reply(Expense.objects.latest(user=user))
        if recurring_expenses_only:
            return ReplyStream(Expense.objects.recurring(user=user))

        expenses = Expense.objects.within_period(
            range_start=last_accounting_entry_date,
            user=user,
            shared_only=shared_only,
            private_only=private_only)

        recurring_expenses = Expense.objects.recurring(user=user)

        if not expenses and not recurring_expenses:
            return Reply(self.storage["default_replies"]["no_expenses_matched"])

        if message.entities.get("sum_expenses"):
            expenses_sum = expenses.sum("price")
            recurring_sum = recurring_expenses.sum("price")
            period_str = (f"{last_accounting_entry_date.strftime('%Y-%m-%d')} - "
                          f"{datetime.now().strftime('%Y-%m-%d')}")
            stream.put(f"Nuvarande konteringsperiod: {period_str}")
            return Reply(f"Summan för {user.username.capitalize()} "
                         f"under denna konteringsperiod är hittills: "
                         f"**{expenses_sum + recurring_sum}**:-.\n"
                         f"Varav återkommande utgifter: **{recurring_sum}**:-\n"
                         f"Varav engångsutgifter: **{expenses_sum}**:-")

        expenses = list(expenses.all())
        if message.entities.get("limit"):
            expenses = expenses[len(expenses) - message.entities["limit"]:]
        else:
            if not private_only:
                expenses.extend(recurring_expenses.all())
        return ReplyStream(expenses)

    @classmethod
    def register_debt(cls, message: Message) -> str:
        """
        Register debts between two users in the application.
        """
        author_is_borrower = message.entities["author_is_borrower"]
        author_is_lender = message.entities["author_is_lender"]
        amount = message.entities["amount"]
        comment = message.entities["comment"]

        if author_is_lender:
            # author_is_lender supersedes author_is_borrower
            lender = message.user
            borrower = extract_username(message, "other_person")
            borrower = User.objects.from_username_or_alias(borrower)
        elif author_is_borrower:
            borrower = message.user
            lender = extract_username(message, "other_person")
            lender = User.objects.from_username_or_alias(lender)
        else:
            lender = message.user
            borrower = extract_username(message, "other_person")
            borrower = User.objects.from_username_or_alias(borrower)
            author_is_lender = True

        if borrower == lender:
            return "Jag förstår inte vem som lånat av vem? " \
                   "Försök igen :slight_smile:"

        # Create the debt entry
        Debt.objects.create(borrower=borrower,
                            lender=lender,
                            amount=amount,
                            comment=comment)
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
        if message.entities["author_is_borrower"]:
            borrower = message.user
        else:
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

        if message.entities["individual"]:
            for debt in Debt.objects.filter(borrower=borrower):
                reply_stream.put(debt)
        else:
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

        try:
            mentioned_user = User.objects.from_username_or_alias(mentioned_user)
        except (IndexError, ValueError):
            pyttman.logger.log(f"User not found for entity "
                               f"provided: '{mentioned_user}'")
            return Reply(self.storage["default_replies"]["no_users_matches"])

        if author_is_borrower:
            lender = mentioned_user
            borrower = message.user
        else:
            lender = message.user
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

    def calculate_split_expenses(self, message):
        """
        Perform an accounting entry, splitting expenses and create a balance
        sheet for users involved in the shared expenses' calculation.
        """
        calculator = SharedFinancesCalculator()
        participant_users = calculator.get_enrolled_users()

        # If there's an accounting entry, use that as the start date for the expenses to get
        datetime_format = pyttman.app.settings.DATETIME_FORMAT
        date_format = pyttman.app.settings.DATETIME_FORMAT
        period_start, period_end = None, None

        for dt_format in (datetime_format, date_format):
            try:
                if (period_start := message.entities["period_start"]) is not None:
                    period_start = datetime.strptime(period_start, dt_format)
                else:
                    period_start = self._get_last_accounting_entry_datetime()

                if (period_end := message.entities["period_end"]) is not None:
                    period_end = datetime.strptime(period_end, dt_format)
                else:
                    period_end = datetime.utcnow()
            except ValueError:
                continue
            else:
                break

        if None in (period_start, period_end):
            return Reply("Jag förstår inte vilken period du vill kontera för. "
                         "Ange start- och slutdatum för perioden.")

        try:
            calculations = calculator.calculate_split(
                participant_users=participant_users,
                range_start=period_start,
                range_end=period_end)
        except ValueError:
            return Reply("Åtminstone en användare har inte angivit månadsinkomst.")

        reply_stream = ReplyStream()
        accounting_entry = AccountingEntry()
        dt_fmt = pyttman.app.settings.DATETIME_FORMAT
        reply_stream.put(f"**Konteringsunderlag**: {datetime.now().strftime(dt_fmt)}")
        period = f"**{period_start.strftime('%Y-%m-%d')} - " \
                 f"{period_end.strftime('%Y-%m-%d')}**"
        reply_stream.put(f"Konteringsperiod: {period}")
        msg = f"**Konteringsperiod: {period}**\n"
        valid = False

        while calculations:
            calculation = calculations.pop()
            username = calculation.user.username.capitalize()
            accounting_entry.participants.append(calculation.user)

            msg = f"\n:moneybag: **{username}:**\n"
            msg += f"**Summa:** {calculation.paid_amount:.2f}:- \n" \
                   f"**Belastning:** {calculation.quota_of_total * 100:.2f}% av " \
                   f"totalen {calculator.total_expense_sum:.2f}:-.\n"
            if calculation.recurring_expenses:
                msg += f"**Varav återkommande utgifter:** {calculation.recurring_expenses:.2f}:- \n"

            msg += f"**Månadslön:** {calculation.income_quotient * 100:.2f}% av den " \
                   f"totala inkomsten av deltagarna.\n"

            if calculation.ingoing_compensation:
                msg += f"**Ska kompenseras med:** {calculation.ingoing_compensation:.2f}:- från övriga " \
                       f"deltagare."
            elif calculation.outgoing_compensation:
                msg += f"**Ska kompensera andra med** {calculation.outgoing_compensation:.2f}:-"
            else:
                msg += f"**{username} har betalat exakt sin kvot och ska varken " \
                       f"kompenseras eller kompensera andra."

            valid = True
            reply_stream.put(msg)

        accounting_entry.accounting_result = msg
        if not valid:
            return Reply("Det finns inga utgifter att kontera för, sedan förra konteringen: "
                         f"{period_start.strftime('%Y-%m-%d %H:%M')}")
        if message.entities["close_current_period"]:
            accounting_entry.save()
            reply_stream.put("Kontering sparad. Utgifter som läggs till från och med nu "
                             "kommer ingå i ett nytt resultat.")
        return reply_stream

    @staticmethod
    def _get_last_accounting_entry_datetime() -> datetime | None:
        """
        Get the date of the last accounting entry. If there's no entry, return None.
        """
        if last_account_entry := AccountingEntry.objects.order_by('-created').first():
            return last_account_entry.created
        return None

    @classmethod
    def delete_last_created_account_entry(cls) -> None:
        """
        Deletes the most-recent accounting entry object.
        """
        if last_entry := AccountingEntry.objects.order_by("-created").first():
            last_entry.delete()
            return last_entry
        return None

    @staticmethod
    def delete_last_expense(message):
        """
        Delete the last expense entry.
        """
        last_expense = Expense.objects.latest(user=message.user)
        last_expense.delete()
        return last_expense
