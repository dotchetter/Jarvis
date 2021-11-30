
from datetime import datetime
import mongoengine
import pandas
from mongoengine import EmbeddedDocument, Document, QuerySet
from pyttman.core.communication.models.containers import Message

from jarvis.abilities.finances.month import Month
from jarvis.meta import ExpenseQuerySet, UserQuerySet


class User(Document):
    """
    A platform-independent User for the Jarvis
    application.

    :field name:
        String, username of a user.
    """
    username = mongoengine.StringField(required=True)
    aliases = mongoengine.ListField(mongoengine.DynamicField())
    meta = {"queryset_class": UserQuerySet}

    @staticmethod
    def get_by_alias_or_username(alias_or_username: str) -> QuerySet:
        """
        Offers a simpler way to find a User by a string
        which could either be an alias or the correct
        username.
        :param alias_or_username:
        :return: QuerySet
        :raise: ValueError, if no user is found by either username or alias
        """
        # Casefold and truncate any special characters
        alias_or_username = Message(alias_or_username).sanitized_content().pop()
        user_by_username = User.objects.filter(username=alias_or_username)
        user_by_alias = User.objects.filter(aliases__icontains=alias_or_username)

        # Always prioritize username since it's a direct lookup
        if len(user_by_username):
            return user_by_username
        elif len(user_by_alias):
            return user_by_alias
        raise ValueError("No user matched query by username or alias")


class Expense(Document):
    """
    This model represents an Expense made by a user.
    The expense is stored for the user who recorded it
    and tracks its name and price. Timestamp of purchase
    in the field 'created' defaults to time of instantiation.
    """
    output_date_format = "%y-%m-%d"
    expense_name = mongoengine.StringField(required=True, max_length=200)
    user_reference = mongoengine.ReferenceField(User, required=True)
    price = mongoengine.IntField(required=True, min_value=0)
    created = mongoengine.DateField(default=datetime.now())

    meta = {"queryset_class": ExpenseQuerySet}

    def __str__(self):
        """
        UI friendly string, for easy visualization in chat.
        :return: str
        """
        sep = "\n" + ("-" * 20) + "\n"
        name = f":pinched_fingers: **{self.expense_name}**\n"
        price = f":money_with_wings: {self.price}:-\n"
        date = f":calendar: **{self.created.strftime(self.output_date_format)}**"
        return name + price + date + sep

    @staticmethod
    def get_expenses_for_period_all_users(month_for_query: str = None) -> QuerySet:
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
        return Expense.objects.filter(created__gte=start_date,
                                      created__lte=end_date)

    @staticmethod
    def get_expenses_for_period_and_user(user: User,
                                         month_for_query: str = None) -> QuerySet:
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
                                      created__gte=start_date,
                                      created__lte=end_date)

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


class Ingredient(EmbeddedDocument):
    """
    Ingredient model used when creating shopping
    lists. Ingredients are Embedded under ShoppingList
    instances.
    """
    name = mongoengine.StringField(max_length=128, required=True)


class ShoppingList(Document):
    """
    Model representing a shopping list.
    The Shopping list contains a list of
    Ingredient instances which compound
    a shopping list.
    """
    ingredients = mongoengine.ListField(mongoengine
                                        .EmbeddedDocumentField(Ingredient))
