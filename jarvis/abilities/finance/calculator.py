from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Collection, Iterable

from mongoengine import Q

from jarvis.abilities.finance.models import Expense, Debt
from jarvis.models import User, Features


class SharedFinancesCalculator:
    """
    Users which have enrolled for joining the split-expenses app,
    will have their bills weighed against the other members which
    have contributed to the shared expenses.

    The resulting data describes who has to compensate whom, and
    by how much, respectively.
    """
    def __init__(self):
        self.total_expense_sum: Decimal = Decimal(0)

    @dataclass
    class SharedExpenseCalculation:
        user: User
        income_quotient: Decimal = field(default=None)
        paid_amount: Decimal = field(default=None)
        expected_paid_amount_based_on_income: Decimal = field(default=None)
        outgoing_compensation: Decimal = field(default=None)
        ingoing_compensation: Decimal = field(default=None)
        quota_of_total: Decimal = field(default=None)

    @classmethod
    def enrolled_usernames(cls):
        return list(cls.get_enrolled_users("username"))

    @classmethod
    def get_enrolled_users(cls, scalar=None) -> Collection[User]:
        enrolled_users = User.objects(
            enrolled_features__contains=Features.shared_finances.value)
        if scalar is None:
            return enrolled_users.all()
        return enrolled_users.scalar(scalar).all()

    def calculate_split(self,
                        participant_users: Iterable[User],
                        range_start: datetime,
                        range_end: datetime = None,
                        ) -> Collection[SharedExpenseCalculation]:
        """
        Calculates the share of the total cost for each individual
        user taking part in the shared finances. Their gross
        salary is taken in to consideration when calculating.
        """
        calculations, processed = [], []
        total_sum = Decimal(
            Expense.objects.within_period(range_start, range_end).sum("price"))

        # Get the total combined income of all participants.
        try:
            combined_income = Decimal(sum((user.profile.gross_income
                                           for user in participant_users)))
        except TypeError:
            raise ValueError("At least one user is missing a gross salary. "
                             "Calculations cannot proceed.")

        # Calculate how much the user has paid, and compare it to how much
        # they should've paid based on their income quotient
        for user in participant_users:
            ingoing_compensation = outgoing_compensation = Decimal(0)
            calculation = self.SharedExpenseCalculation(user=user)
            paid_amount = Expense.objects.within_period(
                user=user,
                start_date=range_start,
                end_date=range_end
            ).sum("price")

            paid_amount = Decimal(paid_amount)
            income_quotient = user.profile.gross_income / combined_income
            expected_paid_amount_based_on_income = total_sum * income_quotient

            if expected_paid_amount_based_on_income > paid_amount:
                outgoing_compensation = expected_paid_amount_based_on_income - paid_amount
            elif expected_paid_amount_based_on_income < paid_amount:
                ingoing_compensation = paid_amount - expected_paid_amount_based_on_income

            calculation.paid_amount = paid_amount
            calculation.income_quotient = income_quotient
            calculation.expected_paid_amount_based_on_income = expected_paid_amount_based_on_income
            calculation.ingoing_compensation = ingoing_compensation
            calculation.outgoing_compensation = outgoing_compensation
            calculation.quota_of_total = calculation.paid_amount / total_sum
            calculations.append(calculation)
        self.total_expense_sum = total_sum
        return calculations

    @classmethod
    def balance_out_debts_for_buckets(cls,
                                      top_paying_bucket: SharedExpenseCalculation,
                                      comparison_bucket: SharedExpenseCalculation):
        """
        Get the compensation_amount balance between two users and see who's
        to compensate whom
        :return: int
        """
        # Find out if the top-paying user owes this user anything.
        top_paying_bucket.outstanding_debt = Debt.objects.filter(
            Q(borrower=top_paying_bucket.user)
            &
            Q(lender=comparison_bucket.user)
        ).sum("amount")

        # And also, see if the user owes the top-paying user anything
        comparison_bucket.outstanding_debt = Debt.objects.filter(
            Q(borrower=comparison_bucket.user)
            &
            Q(lender=top_paying_bucket.user)
        ).sum("amount")

        top_paying_debt_to_user = top_paying_bucket.outstanding_debt
        user_debt_to_top_paying = comparison_bucket.outstanding_debt

        if top_paying_debt_to_user and not user_debt_to_top_paying:
            comparison_bucket.compensation_amount -= top_paying_debt_to_user

        elif user_debt_to_top_paying and not top_paying_debt_to_user:
            comparison_bucket.compensation_amount += user_debt_to_top_paying

        # Both users owe each other money. Find out who owes the most and
        # cancel out their debts.
        elif user_debt_to_top_paying and top_paying_debt_to_user:
            sorted_buckets = sorted((top_paying_bucket, comparison_bucket),
                                    key=lambda bucket: bucket.outstanding_debt)

            largest_debt_bucket = sorted_buckets.pop()
            smallest_debt_bucket = sorted_buckets.pop()

            large_bucket_debt = largest_debt_bucket.outstanding_debt
            small_bucket_debt = smallest_debt_bucket.outstanding_debt
            deducted_debt = max(0, large_bucket_debt - small_bucket_debt)
            largest_debt_bucket.compensation_amount += deducted_debt
            return largest_debt_bucket
