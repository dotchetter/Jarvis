from pyttman.core.ability import Ability
from pyttman.core.containers import Message

from jarvis.abilities.finance.intents import (
    AddExpense,
    GetExpenses,
    CalculateSplitExpenses,
    AddDebt,
    GetDebts,
    RepayDebt
)
from jarvis.abilities.finance.models import Debt
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
               RepayDebt)

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
