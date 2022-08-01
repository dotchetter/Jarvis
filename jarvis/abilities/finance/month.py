from datetime import datetime
from enum import Enum


class Month(Enum):
    """
    Months mapped in Swedish to calendar month
    """
    januari = 1
    februari = 2
    mars = 3
    april = 4
    maj = 5
    juni = 6
    juli = 7
    augusti = 8
    september = 9
    oktober = 10
    november = 11
    december = 12

    @classmethod
    def names_as_list(cls):
        return list(map(lambda i: i.name, cls))

    @classmethod
    def get_month_calendar_int_from_name(cls, month_name: str | None) -> int:
        """
        Returns the calendar int of a month from
        string, if possible - else, current month.
        :param month_name:
        :return: int
        """
        try:
            month_name = month_name.casefold()
            query_month = cls[month_name].value
        except (KeyError, AttributeError):
            query_month = datetime.now().month
        return query_month
