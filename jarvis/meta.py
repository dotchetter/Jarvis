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


class UserQuerySet(QuerySet):
    """
    Custom metaclass for User queries
    """
    def from_alias(self, alias: str):
        """
        Get a User instance by it's alias, if applicable.
        :param alias: str, user alias
        :return: User | None
        """
        return self.filter(aliases__icontains=alias)
