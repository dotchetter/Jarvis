import uuid as uuid

import mongoengine
from mongoengine import Document, EmbeddedDocumentListField, EmbeddedDocument


class PlatformAuthorAlias(EmbeddedDocument):
    """
    The PlatformAuthorAlias model represents Authors
    in Pyttman apps which vary depending on the
    platform the app is connected to through
    Clients.
    """
    uuid = mongoengine.StringField(primary_key=True)
    name = mongoengine.DynamicField()


class User(Document):
    """
    A platform-independent User for the Jarvis
    application.

    The User maps to author id to whichever
    platforms are used with the app.

    Users map One-to-many to PlatformAuthorAlias
    model objects, to represent one user
    on many platforms.
    """
    uuid = mongoengine.StringField(default=uuid.uuid4(), primary_key=True)
    name = mongoengine.StringField()
    platform_author_references = EmbeddedDocumentListField(PlatformAuthorAlias)

