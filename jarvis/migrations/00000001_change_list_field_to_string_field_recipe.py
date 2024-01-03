from jarvis.abilities.recipes.models import Recipe
from jarvis.migrations import expose


def upgrade():
    for recipe in Recipe.objects.all():
        if isinstance(recipe.name, list):
            recipe.name = " ".join(recipe.name)
            recipe.save()


def downgrade():
    for recipe in Recipe.objects.all():
        if isinstance(recipe.name, str):
            recipe.name = recipe.name.split()
            recipe.save()


expose()
