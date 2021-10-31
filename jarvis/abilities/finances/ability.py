import sys

import mongoengine
from pyttman import settings
from pyttman.core.ability import Ability

from jarvis.abilities.finances.intents import AddExpenseIntent, GetExpensesIntent


class FinanceAbility(Ability):
    """
    This Ability class holds private-finance related
    Intents in Jarvis.

    Jarvis helps us collect and keep track of our
    expenses at home, to make splitting bills fair
    and square.
    """
    intents = (AddExpenseIntent, GetExpensesIntent)

    def configure(self) -> None:
        """
        Configure hook method, executed before the app starts
        :return: None
        """
        # Connect to the appropriate MongoDB Atlas database
        if settings.DEV_MODE:
            settings.MONGO_DB_CONFIG["db"] = settings.DB_NAME_DEV
        else:
            settings.MONGO_DB_CONFIG["db"] = settings.DB_NAME_PROD

        mongoengine.connect(**settings.MONGO_DB_CONFIG)

        # Set up a default reply when no expenses are found
        self.storage.put("default_replies",
                         {"no_expenses_matched": "Det finns inga utgifter "
                                                 "sparade med angivna "
                                                 "kriterier",

                          "no_users_matches":    "Jag hittade ingen "
                                                 "användare för sökningen. "
                                                 "Om du angav ett namn, "
                                                 "kontrollera stavningen. "
                                                 "Om du inte angav något, "
                                                 "kontrollera att du är "
                                                 "registrerad."})

        if settings.INTERACTIVE_SHELL is True:
            import IPython
            IPython.embed()
            sys.exit(0)
