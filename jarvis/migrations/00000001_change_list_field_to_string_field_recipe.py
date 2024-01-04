from jarvis.abilities.recipes.models import Recipe

__doc__ = "Change the name field in Recipe to Text field instead of List field"


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
