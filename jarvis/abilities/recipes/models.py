from datetime import datetime

import mongoengine as me


class Recipe(me.Document):
    """
    The recipe model holds a URL to a recipe, and
    refers to the user that created it.

    For quick searching, the name of the recipe is
    also stored.
    """
    created = me.DateTimeField(defalt=lambda: datetime.now())
    user = me.ReferenceField("User", required=False)
    url = me.StringField(required=True)
    name = me.ListField(required=True)
    comment = me.StringField(required=False)

    @property
    def pretty(self):
        name = " ".join(self.name)
        output = f"**{name}**\n{self.url}"
        if self.user is not None:
            output += f"\nSkapad av {self.user.username}"
        return output

    def __str__(self):
        return self.pretty
