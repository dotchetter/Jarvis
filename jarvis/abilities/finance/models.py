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

    def latest(self):
        """
        Returns the most recently recorded Expense.
        :return:
        """
        return self.order_by("-created").first()


class Expense(me.Document):
    """
    This model represents an Expense made by a user.
    The expense is stored for the user who recorded it
    and tracks its name and price. Timestamp of purchase
    in the field 'created' defaults to time of instantiation.
    """
    output_date_format = "%y-%m-%d %H:%M"
    expense_name = me.StringField(required=True, max_length=200)
    user_reference = me.ReferenceField(User, required=True)
    price = me.IntField(required=True, min_value=0)
    created = me.DateTimeField(default=lambda: datetime.now())
    account_for = me.DateField(default=None)
    name = me.StringField(required=False)

    meta = {"queryset_class": ExpenseQuerySet}

    def __str__(self):
        """
        UI friendly string, for easy visualization in chat.
        :return: str
        """
        sep = "\n" + ("-" * 20) + "\n"
        name = f":eyes: **{self.expense_name}**\n"
        price = f":money_with_wings: **{self.price}**:-\n"

        account_month = Month(self.account_for.month).name.capitalize()
        year = self.account_for.year
        account_month = f":calendar: **{account_month} {year}**\n"
        created_date = self.created.strftime(self.output_date_format)
        created_date = f":clock: **{created_date}**\n"
        return name + price + created_date + account_month + sep

    @staticmethod
    def get_expenses_for_period_all_users(
            month_for_query: str = None
    ) -> me.QuerySet:
        """
        Returns Expense instances for all users, in the provided
        month.
        :param month_for_query: Name of a month or None, in which case the
                                query defaults to the current month at time
                                of query
        :return: QuerySet[Expense]
        """
        query_month = Expense.get_month_calendar_int_from_name(month_for_query)
        start_date, end_date = Expense.get_date_range_for_query(query_month)
        return Expense.objects.filter(account_for__gte=start_date.month,
                                      account_for__lte=end_date.month)

    @staticmethod
    def get_expenses_for_period_and_user(user: User,
                                         month_for_query: str = None
                                         ) -> me.QuerySet:
        """
        Returns Expense instances for given user
        recorded in the given month.

        :param user: User owning the Expense documents
        :param month_for_query: Name of a month or None, in which case the
                                query defaults to the current month at time
                                of query
        :return: QuerySet[Expense]
        """
        query_month = Expense.get_month_calendar_int_from_name(month_for_query)
        start_date, end_date = Expense.get_date_range_for_query(query_month)
        return Expense.objects.filter(user_reference=user,
                                      account_for__gte=start_date,
                                      account_for__lte=end_date)

    @staticmethod
    def get_month_calendar_int_from_name(month_for_query) -> int:
        """
        Returns the calendar int of a month from
        string, if possible - else, current month.
        :param month_for_query:
        :return: int
        """
        try:
            query_month = Month[month_for_query].value
        except KeyError:
            query_month = datetime.now().month
        return query_month

    @staticmethod
    def get_date_range_for_query(query_month: int,
                                 periods: int = 1) -> tuple[datetime.date,
                                                            datetime.date]:
        """
        Returns date period range with
        provided name of the month to query.
        Say, the month name is "october": the range will
        start the first day of october and end on the last.

        :param periods: Amount of months to include in the range
        :param query_month: int, calendar int of the month of interest
        :return: tuple[datetime.date, datetime.date]
        """

        # Queries only apply for the current year.
        query_year = datetime.now().year

        # pandas.date_range is conservative; if 1 period is desired,
        # to include the stop date of the same month, it needs to
        # be included explicitly.
        periods += 1
        query_date_from = datetime(year=query_year,
                                   month=query_month,
                                   day=1).date()

        # Adjust one month back in time for the period to
        # render the period correctly (beginning to end of month)
        query_date_from -= pandas.DateOffset(months=1)

        # Pandas date_range with two months left, right with the rightmost
        # one being 1 month in the future, exactly
        timezone = datetime.utcnow().astimezone().tzinfo  # settings.TIME_ZONE
        start_date, end_date = pandas.date_range(start=query_date_from,
                                                 periods=periods,
                                                 tz=timezone,
                                                 freq="M")

        # Correct for the last 24 hours hrs of the previous month; we want
        # the start to be from 1/10 00:00:00 to 31/10 00:00:00 for example,
        # not 31/9 00:00:00 to 31/10 00:00:00
        start_date += pandas.DateOffset(days=1)
        return start_date, end_date


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
    created = me.DateTimeField(default=lambda: datetime.now())

    def __str__(self):
        """
        UI friendly string, for easy visualization in chat.
        :return: str
        """
        sep = "\n" + ("-" * 20) + "\n"
        lender = f":bust_in_silhouette: **" \
                 f"{self.lender.username.capitalize()}**\n"
        amount = f":money_with_wings: **{self.amount}:-**\n"

        return lender + amount + sep


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
    top_paying_user: User = me.ReferenceField(User, required=False)
    accounting_result: str = me.StringField(required=True)
