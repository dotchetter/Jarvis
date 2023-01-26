from pyttman.testing import PyttmanTestCase

from jarvis.abilities.finance.ability import FinanceAbility
from jarvis.abilities.finance.calculator import SharedFinancesCalculator
from jarvis.abilities.finance.models import Expense
from jarvis.models import User, Features, UserProfile


class TestSharedFinancesCalculator(PyttmanTestCase):

    dev_mode = True

    def setUp(self) -> None:
        [i.delete() for i in Expense.objects.all()]
        self.ability = FinanceAbility()

        if user := User.objects(username="test_user_1"):
            user.delete()
        if user := User.objects(username="test_user_2"):
            user.delete()
        if user := User.objects(username="test_user_3"):
            user.delete()

        test_user_1 = User(username="test_user_1")
        test_user_1.enrolled_features.append(Features.shared_finances)
        test_user_1.profile = UserProfile()
        test_user_1.profile.gross_income = 50_000
        test_user_1.profile.save()
        test_user_1.save()

        test_user_2 = User(username="test_user_2")
        test_user_2.profile = UserProfile()
        test_user_2.enrolled_features.append(Features.shared_finances)
        test_user_2.profile.gross_income = 35_000
        test_user_2.profile.save()
        test_user_2.save()

        test_user_3 = User(username="test_user_3")
        test_user_3.profile = UserProfile()
        test_user_3.enrolled_features.append(Features.shared_finances)
        test_user_3.profile.gross_income = 40_000
        test_user_3.profile.save()
        test_user_3.save()

        self.test_user_1 = test_user_1
        self.test_user_2 = test_user_2
        self.test_user_3 = test_user_3

    def test_calculate_split(self):
        for i in range(10):
            Expense(expense_name="test", price=10_000, user_reference=self.test_user_1).save()
            Expense(expense_name="test", price=500, user_reference=self.test_user_2).save()
            Expense(expense_name="test", price=100, user_reference=self.test_user_3).save()

        calculator = SharedFinancesCalculator()
        enrolled_users = list(calculator.get_enrolled_users("username"))

        self.assertIn(self.test_user_1.username, enrolled_users)
        self.assertIn(self.test_user_2.username, enrolled_users)
        self.assertIn(self.test_user_3.username, enrolled_users)

        # The calculations contain a re-organized spread of the costs
        # among the enrolled users. The balance between them is split
        # but also offset by their respective income. The higher the
        # income, the bigger the share of the costs for that user.

        total_expenses_sum = 106_000
        calculations = calculator.calculate_split()

        outgoing_compensation_sum = 0
        calculation_with_ingoing_compensation = None
        for calculation in calculations:
            if calculation.outgoing_compensation:
                outgoing_compensation_sum += calculation.outgoing_compensation
            else:
                calculation_with_ingoing_compensation = calculation

        self.assertIsNotNone(calculation_with_ingoing_compensation)
        # Assert that all outgoing compensations matches the one with
        # an expected ingoing compensation
        self.assertEqual(outgoing_compensation_sum,
                         calculation_with_ingoing_compensation
                         .ingoing_compensation)
        self.fail("Not yet implemented")