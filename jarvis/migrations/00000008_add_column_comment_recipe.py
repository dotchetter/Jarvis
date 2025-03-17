from datetime import date, datetime

from jarvis.abilities.finance.models import AccountingEntry, Expense
from jarvis.abilities.recipes.models import Recipe

__doc__ = "Create new field 'comment' on Recipe table, set to '' for all existing rows."

def upgrade():

    failed_objects, succeeded_objects = [], []
    for recipe in Recipe.objects.all():
        try:
            recipe.comment = ""
            recipe.save()
        except Exception:
            failed_objects.append(recipe)
        else:
            succeeded_objects.append(recipe)

    print(f"Successfully updated {len(succeeded_objects)} objects.")
    print(f"Failed to update {len(failed_objects)} objects.")


def downgrade():
    for recipe in Recipe.objects.all():
        del recipe.comment
        recipe.save()