import unittest

# Develop unittests for your intents here
from pyttman.core.containers import Message
from pyttman.core.storage.basestorage import Storage

from jarvis.abilities.finance.intents import AddExpense


class TestAddExpenseIntent(unittest.TestCase):

    def setUp(self) -> None:
        self.add_expense_intent = AddExpense()
        self.add_expense_intent.storage = Storage()
