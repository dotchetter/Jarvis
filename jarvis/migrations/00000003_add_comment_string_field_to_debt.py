from mongoengine import StringField
from jarvis.abilities.finance.models import Debt

column_to_add = StringField(required=False)
column_name = "comment"

__doc__ = "Assign a 'comment' field to the Debt model."


def upgrade():
    Debt.comment = column_to_add

    for debt in Debt.objects.all():
        if hasattr(debt, column_name):
            continue
        debt.comment = ""
        debt.save()


def downgrade():
    for debt in Debt.objects.all():
        if hasattr(debt, column_name):
            del debt.comment
            debt.save()
