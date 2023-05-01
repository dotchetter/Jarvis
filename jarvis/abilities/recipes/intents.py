from pyttman.core.containers import ReplyStream, Reply, Message
from pyttman.core.entity_parsing.fields import StringEntityField
from pyttman.core.intent import Intent

from jarvis.abilities.recipes.models import Recipe
from jarvis.identifiers import UrlIdentifier
from jarvis.models import User


class AddRecipe(Intent):
    """
    Add a recipe to the database.
    """
    lead = ("spara",)
    trail = ("recept",)

    name = StringEntityField(span=10)
    url = StringEntityField(identifier=UrlIdentifier)

    def respond(self, message: Message) -> Reply | ReplyStream:
        name = message.entities.get("name").split()
        url = message.entities.get("url")
        user = User.objects.from_message(message)
        recipe = Recipe.objects.create(user=user,
                                       name=name,
                                       url=url)
        return Reply(f"Receptet har sparats, tack!\n{recipe}")


class GetRecipes(Intent):
    """
    Get recipes based on provided name.
    """
    lead = ("sök", "visa", "hitta")
    trail = ("recept",)

    name = StringEntityField(span=10)

    def respond(self, message: Message) -> Reply | ReplyStream:
        keyword = message.entities.get("name")
        if not (matching_recipes := Recipe.objects.from_keyword(keyword).all()):
            return Reply("Jag hittade inga recept med det namnet.")
        stream = ReplyStream()
        for recipe in matching_recipes:
            stream.put(Reply(recipe.url))
        return stream
