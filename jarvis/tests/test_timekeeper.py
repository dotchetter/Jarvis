import unittest

# Develop unittests for your intents here
from pyttman.core.containers import Message
from pyttman.core.storage.basestorage import Storage
from pyttman.testing import PyttmanTestCase

from jarvis.abilities.finance.intents import AddExpense
from jarvis.abilities.timekeeper.ability import TimeKeeper


class TestAddExpenseIntent(PyttmanTestCase):

    dev_mode = True

    def setUp(self) -> None:
        self.add_expense_intent = AddExpense()
        self.add_expense_intent.storage = Storage()

    def test_get_worked_hours(self):
        message = Message(entities={"project_name": None,
                                    "sum_for_today": False,
                                    "sum_for_month": False})

        ability = TimeKeeper()
        hours = ability.get_worked_hours(message)
        hours
