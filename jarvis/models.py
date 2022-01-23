import mongoengine
from mongoengine import EmbeddedDocument, Document


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
