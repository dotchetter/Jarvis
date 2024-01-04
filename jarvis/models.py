import enum
from decimal import Decimal
import mongoengine as me
from mongoengine import QuerySet
from pyttman.core.containers import Message


class MigrationVersion(me.Document):
    """
    This model is used to keep track of the current
    migration version of the database.
    """
    version = me.IntField(required=True, default=0)


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
        sanitized_name = Message(name).sanitized_content().pop()
        return self.from_username_or_alias(sanitized_name)


class Features(enum.Enum):
    """
    Available options for features
    """
    shared_finances = 0
    timekeeper = 1


class UserProfile(me.Document):
    """
    Holds various personal attributes
    """
    _gross_income = me.DecimalField(default=None)
    user = me.ReferenceField("User")

    @property
    def gross_income(self) -> Decimal:
        return self._gross_income

    @gross_income.setter
    def gross_income(self, value: Decimal):
        if isinstance(value, float):
            self._gross_income = Decimal.from_float(value)
        else:
            self._gross_income = Decimal(value)


class User(me.Document):
    """
    A platform-independent User for the Jarvis
    application.

    :field name:
        String, username of a user.
    """
    _profile = me.ReferenceField(UserProfile, null=True)
    username = me.StringField(required=True, unique=True)
    aliases = me.ListField(me.DynamicField())
    meta = {"queryset_class": UserQuerySet}
    enrolled_features = me.ListField(me.IntField())
    weight_entries = me.ListField(me.ReferenceField("WeightEntry"))

    @property
    def profile(self) -> UserProfile:
        if self._profile is None:
            self._profile = UserProfile()
        return self._profile
