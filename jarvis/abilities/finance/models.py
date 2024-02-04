from datetime import datetime

import mongoengine as me
import pandas
from mongoengine import QuerySet

from jarvis.abilities.finance.month import Month
from jarvis.models import User


class ExpenseQuerySet(QuerySet):
    """
    Custom metaclass for the QuerySetManager
    used when querying the Expense model.
    """

    def latest(self, user=None):
        """
        Returns the most recently recorded Expense.
        :return:
        """
        result = self.order_by("-created")
        if user is not None:
            result = result.filter(user_reference=user)
        return result.first()

    def recurring(self, user: User = None) -> QuerySet:
        """
        Returns all recurring expenses.
        :param user: User owning the Expense documents
        :return: QuerySet[Expense]
        """
        return self.filter(user_reference=user,
                           recurring_monthly=True)

    def within_period(self,
                      range_start: datetime,
                      range_end: datetime,
                      user: User = None) -> QuerySet:
        """
        Returns Expense instances for given user
        """
        return self.filter(user_reference=user,
                           created__gte=range_start,
                           created__lte=range_end)


class Expense(me.Document):
    """
    This model represents an Expense made by a user.
    The expense is stored for the user who recorded it
    and tracks its name and price. Timestamp of purchase
    in the field 'created' defaults to time of instantiation.
    """
    name = me.StringField(required=False)
    output_date_format = "%y-%m-%d %H:%M"
    expense_name = me.StringField(required=True, max_length=200)
    user_reference = me.ReferenceField(User, required=True)
    price = me.IntField(required=True, min_value=0)
    created = me.DateTimeField(default=lambda: datetime.now(
        tz=app.settings.TIME_ZONE))
    account_for = me.DateField(default=lambda: datetime.now(
        tz=app.settings.TIME_ZONE))
    recurring_monthly = me.BooleanField(default=False)

    meta = {"queryset_class": ExpenseQuerySet}

    def __str__(self):
        """
        UI friendly string, for easy visualization in chat.
        :return: str
        """
        sep = "\n" + ("-" * 20) + "\n"
        name = f":eyes: **{self.expense_name}**\n"
        price = f":money_with_wings: **{self.price}**:-\n"

        account_month = Month(self.created.month).name.capitalize()
        year = self.account_for.year
        account_month = f":calendar: **{account_month} {year}**\n"
        created_date = self.created.strftime(self.output_date_format)
        created_date = f":clock: **{created_date}**\n"
        return name + price + created_date + account_month + sep


class Debt(me.Document):
    """
    An outstanding compensation_amount from one user to another.
    Debts can be accounted for when accounting for expenses,
    as they will inflict 100% of their amount as reduction to
    an initial compensation to the lender.
    """
    borrower: User = me.ReferenceField(User, required=True)
    lender: User = me.ReferenceField(User, required=True)
    amount: float = me.FloatField(default=0.0)
    created: datetime = me.DateTimeField(default=lambda: datetime.now())
    comment = me.StringField(required=False)

    def __str__(self):
        """
        UI friendly string, for easy visualization in chat.
        :return: str
        """
        sep = "\n" + ("-" * 20) + "\n"
        lender = f":bust_in_silhouette: **" \
                 f"{self.lender.username.capitalize()}**\n"
        amount = f":money_with_wings: **{self.amount}:-**\n"
        comment = f":speech_left: **{self.comment}**\n" if self.comment else ""
        return lender + amount + comment + sep


class AccountingEntry(me.Document):
    """
    This model represents an accounting performed by
    a user.

    Accounting records hold the state of balances between
    shared expenses and debts among users.
    Whenever a report is created by the user, the data
    is returned and then stored in this document for
    later retrieval.
    """
    participants: list[User] = me.ListField(me.ReferenceField(User, required=True))
    accounting_result: str = me.StringField(required=True)
    created = me.DateField(default=datetime.now())
