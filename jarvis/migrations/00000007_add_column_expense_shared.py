from datetime import date, datetime

from jarvis.abilities.finance.models import AccountingEntry, Expense
from jarvis.abilities.recipes.models import Recipe

__doc__ = "Create new field 'shared' on Expense table, set to True for all existing rows."

def upgrade():

    failed_objects, succeeded_objects = [], []
    for expense in Expense.objects.all():
        try:
            expense.shared = True
            expense.save()
        except Exception as e:
            failed_objects.append(expense)
        else:
            succeeded_objects.append(expense)

    print(f"Successfully updated {len(succeeded_objects)} Expense objects.")
    print(f"Failed to update {len(failed_objects)} Expense objects.")


def downgrade():
    for expense in Expense.objects.all():
        del expense.shared
        expense.save()
