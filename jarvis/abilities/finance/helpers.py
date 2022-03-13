from dataclasses import dataclass

from jarvis.abilities.administrative.models import User
from jarvis.models import AppEnrollment
from jarvis.abilities.finance.models import Expense


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
        debt: int

    @classmethod
    def calculate_split(cls):
        app_enrollment = AppEnrollment.objects.get(shared_expenses=True)
        enrolled = User.objects.filter(enrolled_apps=app_enrollment)
        expense_buckets, processed = [], []
        total_sum = 0

        for user in enrolled:
            expenses = Expense.get_expenses_for_period_and_user(user=user)
            amount = expenses.sum("price")
            bucket = cls.SharedExpenseBucket(user, amount, 0)
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
            bucket.debt = (quotient - bucket.paid_amount)
            processed.append(bucket)

        processed.append(top_paying_bucket)
        return processed
