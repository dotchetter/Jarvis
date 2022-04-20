import mongoengine as me
from mongoengine import QuerySet
from pyttman.core.containers import Message


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


class AppEnrollment(me.Document):
    """
    Embedded document, representing app names provided
    in Jarvis, allowing users to enroll and/or de-enroll from
    certain optional functionality in Jarvis.
    """
    shared_expenses = me.BooleanField(default=False)
    work_shift = me.BooleanField(default=False)


class User(me.Document):
    """
    A platform-independent User for the Jarvis
    application.

    :field name:
        String, username of a user.
    """
    username = me.StringField(required=True)
    aliases = me.ListField(me.DynamicField())
    meta = {"queryset_class": UserQuerySet}
    enrolled_apps = me.ReferenceField(AppEnrollment)
