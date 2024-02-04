from datetime import date, datetime

from jarvis.abilities.finance.models import AccountingEntry

__doc__ = "Change the 'created' field for AccountingEntry to a DateTimeField."


def upgrade():
    for accounting_entry in AccountingEntry.objects.all():
        if isinstance(accounting_entry.created, date):
            accounting_entry.created = datetime.combine(accounting_entry.created, datetime.min.time())
            try:
                accounting_entry.save()
            except Exception as e:
                print(f"Failed to save accounting entry {accounting_entry.id}: {e}")


def downgrade():
    for accounting_entry in AccountingEntry.objects.all():
        accounting_entry.created = accounting_entry.created.date()
        try:
            accounting_entry.save()
        except Exception as e:
            print(f"Failed to save accounting entry {accounting_entry.id}: {e}")
