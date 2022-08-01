from dataclasses import dataclass
from typing import Collection

from mongoengine import Q

from jarvis.abilities.finance.models import Expense, Debt
from jarvis.models import AppEnrollment, User


class SharedExpensesApp:
    """
    Users which have enrolled for joining the split-expenses app,
    will have their bills weighed against the other members which
    have contributed to the shared expenses.

    The resulting data describes who has to compensate whom, and
    by how much, respectively.
    """

    @dataclass
    class SharedExpenseBucket:
        user: User
        paid_amount: int
        compensation_amount: int
        outstanding_debt: int

    @classmethod
    def enrolled_usernames(cls):
        return list(cls.get_enrolled_users("username"))

    @classmethod
    def get_enrolled_users(cls, scalar=None) -> Collection[User]:
        app_enrollment = AppEnrollment.objects.get(shared_expenses=True)
        res = User.objects.filter(enrolled_apps=app_enrollment)
        if scalar is None:
            return res.all()
        return res.scalar(scalar).all()

    @classmethod
    def calculate_split(cls, month_for_query: str | None = None):
        enrolled = cls.get_enrolled_users()
        expense_buckets, processed = [], []
        total_sum = 0

        for user in enrolled:
            expenses = Expense.get_expenses_for_period_and_user(
                user=user,
                month_for_query=month_for_query)
            amount = expenses.sum("price")
            bucket = cls.SharedExpenseBucket(user, amount, 0, 0)
            expense_buckets.append(bucket)
            total_sum += amount

        expense_buckets = sorted(expense_buckets,
                                 key=lambda i_bucket: i_bucket.paid_amount)

        # Split the total sum by the paid_amount of participants
        quotient = total_sum / len(enrolled)

        # Sorted by tbe user who paid the most
        top_paying_bucket = expense_buckets.pop()

        while expense_buckets:
            bucket = expense_buckets.pop()
            bucket.compensation_amount = (quotient - bucket.paid_amount)
            processed.append(bucket)

        processed.append(top_paying_bucket)
        return processed

    @classmethod
    def balance_out_debts_for_buckets(cls,
                                      top_paying_bucket: SharedExpenseBucket,
                                      comparison_bucket: SharedExpenseBucket):
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
