from datetime import datetime

import mongoengine
import uuid as uuid

from mongoengine import Document, EmbeddedDocument, EmbeddedDocumentListField


class Expense(Document):
    """
    MongoDB MongoEngine model

    This model represents an Expense made by a user.
    The expense is stored for the user who recorded it
    and tracks its name and price. Timestamp of purchase
    in the field 'created' defaults to time of instantiation.
    """
    author = mongoengine.DynamicField(required=True)
    name = mongoengine.StringField(required=True, max_length=200)
    price = mongoengine.IntField(required=True, min_value=0)
    created = mongoengine.DateField(default=datetime.now())


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
    ingredients = mongoengine.ListField(mongoengine.EmbeddedDocumentField(Ingredient))


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
