from pyttman.core.ability import Ability

from jarvis.abilities.finance.intents import (
    AddExpense,
    GetExpenses,
    CalculateSplitExpenses,
    AddDebt,
    GetDebts,
    RepayDebt
)


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
