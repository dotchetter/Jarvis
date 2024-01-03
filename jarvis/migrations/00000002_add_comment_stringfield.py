from mongoengine import StringField

from jarvis.abilities.recipes.models import Recipe
from jarvis.migrations import expose


def upgrade():
    Recipe.comment = StringField(required=False)
    for recipe in Recipe.objects.all():
        if hasattr(recipe, "comment"):
            continue
        recipe.comment = ""


def downgrade():
    for recipe in Recipe.objects.all():
        if isinstance(recipe.name, str):
            recipe.name = recipe.name.split()
            recipe.save()


expose()
