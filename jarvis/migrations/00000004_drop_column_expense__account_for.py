from mongoengine import StringField
from jarvis.abilities.finance.models import Debt, Expense

__doc__ = "Remove the 'account_for' column in Expenses, made redundant"


def upgrade():
    for exp in Expense.objects.all():
        del exp.account_for
        exp.save()


def downgrade():
    for exp in Expense.objects.all():
        exp.account_for = exp.created_at
        exp.save()
