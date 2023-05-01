from pyttman.testing import PyttmanTestCase

from jarvis.abilities.recipes.models import Recipe


class TestRecipes(PyttmanTestCase):
    devmode = True

    def test_add_recipe(self):
        name = "riktigt najs tacopaj".split()
        recipe = Recipe(name=name, url="https://www.ica.se/recept/tacopaj-718120/")
        recipe.save()

        search_string = "tacopaj"
        stored_recipe = Recipe.objects.from_keyword(search_string).first()

        self.assertIsNotNone(stored_recipe)
