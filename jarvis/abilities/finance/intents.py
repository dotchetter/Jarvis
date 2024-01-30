from typing import Union

from pyttman.core.containers import Message, Reply, ReplyStream
from pyttman.core.entity_parsing.fields import TextEntityField, \
    BoolEntityField, IntEntityField, StringEntityField, FloatEntityField
from pyttman.core.intent import Intent

from jarvis.abilities.finance.calculator import SharedFinancesCalculator
from jarvis.abilities.finance.month import Month
from jarvis.models import User


class AddExpense(Intent):
    """
    Add a shared expense.
    """
    lead = ("spara", "ny", "nytt", "new", "save", "store")
    trail = ("utgift", "expense", "utlägg", "purchase")

    expense_name = TextEntityField(span=10)
    store_for_next_month = BoolEntityField(message_contains=("nästa",
                                                             "månad"))
    expense_value = FloatEntityField()
    store_for_username = TextEntityField(valid_strings=SharedFinancesCalculator
                                         .enrolled_usernames)

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        return self.ability.add_expense(message)


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
    month = TextEntityField(valid_strings=Month.names_as_list)
    username_for_query = TextEntityField(
        valid_strings=SharedFinancesCalculator.enrolled_usernames)

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        """
        Isolate for which user the intent is for.
        If the sum is asked for, simply provide only the
        sum - otherwise return all expenses for the
        selected month.
        """
        return self.ability.get_expenses(message)


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

    close_current_period = BoolEntityField(message_contains=("stäng", "lås"))
    month = StringEntityField(valid_strings=Month.names_as_list)

    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        try:
            return self.ability.calculate_split_expenses(message)
        except TypeError:
            return Reply("Det gick inte att utföra uträkningen eftersom "
                         "det finns användare som saknar angiven "
                         "månadsinkomst.")


class EnterMonthlyIncome(Intent):
    """
    Allows users to enter an amount stored as their monthly
    salary in their profile
    """
    lead = ("lön", "månadslön", "inkomst", "income", "salary")
    description = "Ange hur mycket du har i månadslön. Beloppet används " \
                  "som en koefficient när utgifter ska fördelas rättvist " \
                  "mellan deltagare i delade utgifter."

    income = IntEntityField()

    def respond(self, message: Message) -> Reply | ReplyStream:
        current_user = User.objects.from_message(message)
        if income := message.entities["income"]:
            current_user.profile.gross_income = income
            current_user.profile.save()
            current_user.save()
            return Reply(f"Månadsinkomst sparad: {income}:- före skatt.")

        if current_income := current_user.profile.gross_income:
            return Reply(f"Din sparade månadsinkomst är {current_income} "
                         f":- före skatt.")
        return Reply(f"Du har ingen sparad månadsinkomst.")


class AddDebt(Intent):
    """
    Register a debt.
    The debt can either be described as you borrowing from another
    person, or that other person borrowing from you.

    'I've borrowed 200:- from John'   <- You're the borrower
    'John has borrowed 200'           <- You're the lender
    """
    help_string = __doc__
    example = "Jag har lånat 100 kronor av Katrin"
    lead = ("lånat", "låna", "lånade", "borrowed", "borrow")

    author_is_borrower = BoolEntityField(message_contains=("jag", "i"))
    author_is_lender = BoolEntityField(message_contains=("ut", "mig", "me"))
    other_person = TextEntityField(valid_strings=SharedFinancesCalculator
                                   .enrolled_usernames)
    amount = IntEntityField()
    comment = TextEntityField(span=10, prefixes=("för", "till"))

    def respond(self, message: Message) -> Reply | ReplyStream:
        if message.entities["amount"] is None:
            return Reply("Du måste ange belopp på skulden")
        return Reply(self.ability.register_debt(message))


class GetDebts(Intent):
    """
    Returns the sum of the debts registered for a borrower to
    a particular lender.
    """
    lead = ("visa", "lista", "show", "get", "hämta", "hur")
    trail = ("skuld", "skulder", "debts", "lån", "lånat", "lånade", "skyldig")

    author_is_borrower = BoolEntityField(message_contains=("jag", "i"))
    borrower_name = TextEntityField(
        valid_strings=SharedFinancesCalculator.enrolled_usernames)
    individual = BoolEntityField(message_contains=("individuell",
                                                   "individuella",
                                                   "individuellt"))

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.get_debts(message)


class RepayDebt(Intent):
    """
    Allows users to repay an outstanding compensation_amount to other users.
    """
    description = "Återbetalning av en skuld, eller en del av en skuld till " \
                  "en annan användare."
    example = "jag har betalat tillbaka 100:- till <användare>"
    lead = ("betalat", "betala", "återbetalat", "kompensera", "kompenserat")

    repaid_amount = IntEntityField()
    mentioned_user = TextEntityField(
        valid_strings=SharedFinancesCalculator.enrolled_usernames)
    author_is_borrower = BoolEntityField(message_contains=("jag", "i"))

    def respond(self, message: Message) -> Reply | ReplyStream:
        return self.ability.repay_debt(message)


class UndoLastClosingCalculatedExpense(Intent):
    """
    This intent allows users to delete previously accounting records.
    It will delete the most recent entry.
    """
    help_string = __doc__
    lead = ("radera", "ta bort", "ångra")
    trail = ("kontering", "konteringen")

    def respond(self, message: Message) -> Reply | ReplyStream:
        deleted_entry = self.ability.delete_last_created_account_entry()
        if deleted_entry is None:
            return Reply("Det fanns ingen kontering att radera.")
        return Reply(f"Konteringen från {deleted_entry.created} har raderats.")
