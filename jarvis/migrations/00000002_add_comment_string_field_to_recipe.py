from mongoengine import StringField
from jarvis.abilities.recipes.models import Recipe

__doc__ = " Assign a 'comment' field to the Recipe model."


def upgrade():
    Recipe.comment = StringField(required=False)
    for recipe in Recipe.objects.all():
        if hasattr(recipe, "comment"):
            continue
        recipe.comment = ""
        recipe.save()


def downgrade():
    for recipe in Recipe.objects.all():
        if hasattr(recipe, "comment"):
            del recipe.comment
            recipe.save()
