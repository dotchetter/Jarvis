import mongoengine
from mongoengine import Document, QuerySet
from pyttman.core.communication.models.containers import Message

from jarvis.meta import UserQuerySet


class AppEnrollment(Document):
    """
    Embedded document, representing app names provided
    in Jarvis, allowing users to enroll and/or de-enroll from
    certain optional functionality in Jarvis.
    """
    shared_expenses = mongoengine.BooleanField(default=False)


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
    enrolled_apps = mongoengine.ReferenceField(AppEnrollment)

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
        user_by_alias = User.objects.filter(
            aliases__icontains=alias_or_username)

        # Always prioritize username since it's a direct lookup
        if len(user_by_username):
            return user_by_username
        elif len(user_by_alias):
            return user_by_alias
        raise ValueError("No user matched query by username or alias")
