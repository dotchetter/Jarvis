import os
from unittest import TestCase

import certifi
import mongoengine
import pandas
from dotenv import load_dotenv
from mongoengine import QuerySet

from jarvis.abilities.finance.month import Month
from jarvis.models import User
from jarvis.abilities.finance.models import Expense


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
        self.user = User.objects.filter(
            aliases__contains=self.mock_alias).first()
        self.erase_all_expenses_in_db()

    def tearDown(self) -> None:
        self.erase_all_expenses_in_db()

    def test_get_expenses_for_period_and_user(self):
        # Fetch the admin test user from the db, assert expected expenses exist

        # Create a few expenses
        for i in range(1, 11):
            Expense.objects.create(expense_name=f"SomeExpense-Test-{i}",
                                   user_reference=self.user,
                                   price=i)

        # Obtain the expenses for the current month which just registered
        expenses = Expense.get_expenses_for_period_and_user(user=self.user)
        self.assertEqual(sum, expenses.sum("price"))
        self.assertEqual(len(expenses), 10)

    def test_get_date_range_for_query(self):
        for enum_month in Month:
            start_date, end_date = Expense.get_date_range_for_query(
                enum_month.name)

            # Ensure every enum month matches what is returned
            self.assertEqual(start_date.month, enum_month.value)
            self.assertEqual(start_date.month, end_date.month)

    def erase_all_expenses_in_db(self):
        # Clean the db of pre-existing expenses
        for expense in Expense.objects.filter(user_reference=self.user):
            expense.delete()
