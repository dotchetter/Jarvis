from datetime import datetime

import mongoengine


class Expense(mongoengine.Document):
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


class Ingredient(mongoengine.EmbeddedDocument):
    """
    Ingredient model used when creating shopping
    lists. Ingredients are Embedded under ShoppingList
    instances.
    """
    name = mongoengine.StringField(max_length=128, required=True)


class ShoppingList(mongoengine.Document):
    """
    Model representing a shopping list.
    The Shopping list contains a list of
    Ingredient instances which compound
    a shopping list.
    """
    ingredients = mongoengine.ListField(mongoengine.EmbeddedDocumentField(Ingredient))

