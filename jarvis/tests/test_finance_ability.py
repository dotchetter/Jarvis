from datetime import datetime
from decimal import Decimal

from pyttman.core.containers import Message
from pyttman.testing import PyttmanTestCase

from jarvis.abilities.finance.ability import FinanceAbility
from jarvis.abilities.finance.calculator import SharedFinancesCalculator
from jarvis.abilities.finance.models import Expense
from jarvis.models import User, Features


class TestSharedFinancesCalculator(PyttmanTestCase):
    devmode = True

    def setUp(self) -> None:
        [i.delete() for i in Expense.objects.all()]
        self.ability = FinanceAbility()

        for i in range(10):
            if user := User.objects(username=f"test_user_{i}"):
                user.delete()

        test_user_1 = User(username="test_user_1")
        test_user_1.enrolled_features.append(Features.shared_finances.value)
        test_user_1.profile.gross_income = 50_000
        test_user_1.profile.save()
        test_user_1.save()

        test_user_2 = User(username="test_user_2")
        test_user_2.enrolled_features.append(Features.shared_finances.value)
        test_user_2.profile.gross_income = 35_000
        test_user_2.profile.save()
        test_user_2.save()

        test_user_3 = User(username="test_user_3")
        test_user_3.enrolled_features.append(Features.shared_finances.value)
        test_user_3.profile.gross_income = 40_000
        test_user_3.profile.save()
        test_user_3.save()

        test_user_4 = User(username="test_user_4")
        test_user_4.profile.gross_income = 50_000
        test_user_4.profile.save()
        test_user_4.save()

        self.test_user_1 = test_user_1
        self.test_user_2 = test_user_2
        self.test_user_3 = test_user_3
        self.test_user_4 = test_user_4

        self.calculator = SharedFinancesCalculator()

    def _get_enrolled_test_users_in_finance(self):
        for user in self.calculator.get_enrolled_users():
            if user.username.startswith("test_"):
                yield user

    def test_calculate_split(self):

        # Each user makes a purchase. They should split it fairly based
        # on income.
        Expense(expense_name="test", price=1000, user_reference=self.test_user_1).save()
        Expense(expense_name="test", price=500, user_reference=self.test_user_2).save()
        Expense(expense_name="test", price=100, user_reference=self.test_user_3).save()
        users = [user.id for user in self._get_enrolled_test_users_in_finance()]
        self.assertIn(self.test_user_1.id, users)
        self.assertIn(self.test_user_2.id, users)
        self.assertIn(self.test_user_3.id, users)

        # The calculations contain a re-organized spread of the costs
        # among the enrolled users. The balance between them is split
        # but also offset by their respective income. The higher the
        # income, the bigger the share of the costs for that user.
        expected_total_expenses_sum = 1600
        result_total_expenses_sum = 0
        users = list(self._get_enrolled_test_users_in_finance())
        calculations = self.calculator.calculate_split(users)

        # The sum of the outgoing compensation amounts should match the
        # largest outgoing compensation amounts.
        total_ingoing_compensation_for_beneficiaries = 0

        # This amount is what the highest paid person is expected to
        # compensate their two peers in the share pool, combined
        expected_outgoing_compensation_for_highest_earner = 412
        result_outgoing_compensation_for_highest_earner = 0

        for calculation in calculations:
            result_total_expenses_sum += calculation.paid_amount
            total_ingoing_compensation_for_beneficiaries += calculation.outgoing_compensation
            if calculation.ingoing_compensation:
                result_outgoing_compensation_for_highest_earner += calculation.ingoing_compensation

        self.assertEqual(expected_total_expenses_sum, result_total_expenses_sum)
        self.assertEqual(result_outgoing_compensation_for_highest_earner,
                         expected_outgoing_compensation_for_highest_earner)

        # Now test with another high earner, with equally high expenses
        self.test_user_4.enrolled_features.append(Features.shared_finances.value)
        self.test_user_4.save()
        Expense(expense_name="test", price=1000, user_reference=self.test_user_4).save()
        enrolled_users = list(self._get_enrolled_test_users_in_finance())
        self.assertIn(self.test_user_4.id, [i.id for i in enrolled_users])

        calculations = self.calculator.calculate_split(enrolled_users)
        for calculation in calculations:
            if calculation.user is self.test_user_1:
                self.assertEqual(calculation.outgoing_compensation, 0)
                self.assertEqual(calculation.ingoing_compensation, Decimal(257.14))
                break
            elif calculation.user is self.test_user_2:
                self.assertEqual(calculation.outgoing_compensation, 20)
                self.assertEqual(calculation.ingoing_compensation, 0)
                break
            elif calculation.user is self.test_user_3:
                self.assertEqual(calculation.outgoing_compensation, Decimal(494.28))
                self.assertEqual(calculation.ingoing_compensation, 0)
                break
            elif calculation.user is self.test_user_4:
                self.assertEqual(calculation.outgoing_compensation, 0)
                self.assertEqual(calculation.ingoing_compensation, Decimal(257.14))
                break

    def test_calculate_split_expenses(self):
        self.test_user_4.enrolled_features.append(Features.shared_finances.value)
        self.test_user_4.save()
        Expense(expense_name="test", price=1000, user_reference=self.test_user_4).save()
        Expense(expense_name="test", price=1000, user_reference=self.test_user_3).save()

        message = Message(entities={"month": datetime.now().month, "close_current_period": True})
        reply = self.ability.calculate_split_expenses(message)

        expected_rows = 9
        actual_rows = 0
        while reply.qsize():
            actual_rows += 1
            print(reply.get().as_str())
        self.assertEqual(expected_rows, actual_rows)

