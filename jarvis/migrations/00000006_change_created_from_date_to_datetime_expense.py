from datetime import date, datetime

from jarvis.abilities.finance.models import AccountingEntry, Expense
from jarvis.abilities.recipes.models import Recipe

__doc__ = "Change the 'created' field for Expense to a DateTimeField."


def upgrade():
    for expense in Expense.objects.all():

        if isinstance(expense.created, date):
            expense.created = datetime.combine(expense.created, datetime.min.time())
            try:
                expense.save()
            except Exception as e:
                print(f"Failed to save expense {expense.id}: {e}")


def downgrade():
    for accounting_entry in AccountingEntry.objects.all():
        accounting_entry.created = accounting_entry.created.date()
        try:
            accounting_entry.save()
        except Exception as e:
            print(f"Failed to save accounting entry {accounting_entry.id}: {e}")
