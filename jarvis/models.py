import mongoengine as me
from jarvis.meta import UserQuerySet


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
