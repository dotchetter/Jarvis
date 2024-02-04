import os
from unittest import TestCase

import certifi
import mongoengine
from dotenv import load_dotenv

from jarvis.abilities.finance.models import Expense
from jarvis.models import User


class TestExpenseModel(TestCase):
    load_dotenv()

    mongoengine.connect(**{
        "tlsCAFile": certifi.where(),
        "db": os.getenv("MONGO_DB_NAME_DEV"),
        "host": os.getenv("MONGO_DB_URL"),
        "username": os.getenv("MONGO_DB_USER"),
        "password": os.getenv("MONGO_DB_PASSWORD"),
        "port": int(os.getenv("MONGO_DB_PORT"))})

    def setUp(self):
        self.mock_alias = "anonymous"
        self.user = User.objects.first()

    def test_recurring_expenses(self):

        normal_expense = Expense(expense_name="NormalExpense",
                                 user_reference=self.user,
                                 price=100)
        normal_expense.save()
        recurring_expense = Expense(expense_name="RecurringExpense",
                                    user_reference=self.user,
                                    price=100,
                                    recurring_monthly=True)
        recurring_expense.save()

        recurring_expenses_for_user = Expense.objects.recurring(user=self.user)

        self.assertEqual(len(recurring_expenses_for_user), 1)
        self.assertTrue(recurring_expenses_for_user.first().recurring_monthly)

        normal_expenses = Expense.objects.filter(recurring_monthly=False)
        self.assertFalse(normal_expenses.first().recurring_monthly)

        normal_expense.delete()
        recurring_expense.delete()

