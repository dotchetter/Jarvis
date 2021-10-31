from mongoengine import QuerySet


class ExpenseQuerySet(QuerySet):
    """
    Custom metaclass for the QuerySetManager
    used when querying the Expense model.
    """
    def latest(self):
        """
        Returns the most recently recorded Expense.
        :return:
        """
        return self.order_by("-created", ).first()
