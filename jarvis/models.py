class User(Document):
    """
    A platform-independent User for the Jarvis
    application.

    :field name:
        String, username of a user.
    """
    username = mongoengine.StringField(required=True)
    aliases = mongoengine.ListField(mongoengine.DynamicField())

    @staticmethod
    def get_by_alias_or_username(alias_or_username: str) -> QuerySet:
        """
        Offers a simpler way to find a User by a string
        which could either be an alias or the correct
        username.
        :param alias_or_username:
        :return: QuerySet
        :raise: ValueError, if no user is found by either username or alias
        """
        # Casefold and truncate any special characters
        alias_or_username = Message(alias_or_username).sanitized_content().pop()
        user_by_username = User.objects.filter(username=alias_or_username)
        user_by_alias = User.objects.filter(aliases__icontains=alias_or_username)

        # Always prioritize username since it's a direct lookup
        if len(user_by_username):
            return user_by_username
        elif len(user_by_alias):
            return user_by_alias
        raise ValueError("No user matched query by username or alias")
class Expense(Document):
    """
    This model represents an Expense made by a user.
    The expense is stored for the user who recorded it
    and tracks its name and price. Timestamp of purchase
    in the field 'created' defaults to time of instantiation.
    """
    output_date_format = "%y-%m-%d"
    expense_name = mongoengine.StringField(required=True, max_length=200)
    user_reference = mongoengine.ReferenceField(User, required=True)
    price = mongoengine.IntField(required=True, min_value=0)
    created = mongoengine.DateField(default=datetime.now())

    meta = {"queryset_class": ExpenseQuerySet}

    def __str__(self):
        """
        UI friendly string, for easy visualization in chat.
        :return: str
        """
        sep = "\n" + ("-" * 20) + "\n"
        name = f":pinched_fingers: **{self.expense_name}**\n"
        price = f":money_with_wings: {self.price}:-\n"
        date = f":calendar: **{self.created.strftime(self.output_date_format)}**"
        return name + price + date + sep
