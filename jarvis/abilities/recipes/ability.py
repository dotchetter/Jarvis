
"""
This ability holds intents related to the
Recipes feature of the application.
"""

from pyttman.core.ability import Ability
from jarvis.abilities.administrative.intents import *
from jarvis.abilities.recipes.intents import AddRecipe, GetRecipes


class RecipesAbility(Ability):
    """
    Ability class for recipes, storing and retrieving
    recipes in the application
    """
    intents = (AddRecipe, GetRecipes)
