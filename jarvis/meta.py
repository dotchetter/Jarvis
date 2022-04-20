from mongoengine import QuerySet
from pyttman.core.containers import Message


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
        return self.order_by("-created").first()


class UserQuerySet(QuerySet):
    """
    Custom metaclass for User queries
    """
    def from_username(self, username: str):
        """
        Get a user by username
        """
        return self.filter(username=username).first()

    def from_alias(self, alias: str):
        """
        Get a user by one of their aliases.
        """
        return self.filter(aliases__icontains=alias).first()

    def from_username_or_alias(self, name: str):
        """
        Returns a User matching on the string which is either
        a username or an alias.
        If both alias and username should match, username supersedes
        aliases since it's an absolute identifier.
        """
        return self.from_username(username=name) or self.from_alias(name)

    def from_message(self, message: Message):
        """
        Get a User instance by its alias, if applicable.
        """
        try:
            name = message.author.id
        except AttributeError:
            name = message.author
        return self.from_username_or_alias(name)
