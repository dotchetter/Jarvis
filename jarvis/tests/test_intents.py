import unittest
import pyttman


# Develop unittests for your intents here
from pyttman.core.communication.models.containers import Message
from pyttman.core.storage.basestorage import Storage

from jarvis.abilities.finances.ability import AddExpense


class TestAddExpenseIntent(unittest.TestCase):

    def setUp(self) -> None:
        self.add_expense_intent = AddExpense()
        self.add_expense_intent.storage = Storage()

    def test_expense_is_parsed_correctly(self):
        add_expense_message = Message("utlägg Bensin till bilen 234")
        response = self.add_expense_intent.respond(add_expense_message)
        print(response.as_str())
