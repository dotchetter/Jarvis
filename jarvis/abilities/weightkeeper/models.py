from datetime import datetime

import mongoengine as me


class WeightEntry(me.Document):
    """
    Represents a weight entry from a user.
    """
    kilos = me.DecimalField()
    user = me.ReferenceField("User")
    created = me.DateTimeField(default=lambda: datetime.now())
    median = me.DecimalField()
