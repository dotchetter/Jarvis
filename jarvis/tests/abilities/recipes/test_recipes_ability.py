from pyttman.core.containers import Message
from pyttman.testing import PyttmanTestCase

from jarvis.abilities.recipes.intents import AddRecipe
from jarvis.models import User


class TestRecipesAbility(PyttmanTestCase):
    devmode = True

    def setUp(self) -> None:
        self.mock_message = Message("Spara recept kyckling med nudlar"
                                    " från https://www.test.com")

    def test_add_recipe(self):
        intent = AddRecipe()
        self.mock_message.author = "test_user_1"
        self.mock_message.entities["name"] = "kyckling med nudlar"
        self.mock_message.entities["url"] = "https://www.test.com"

        intent.respond(self.mock_message)