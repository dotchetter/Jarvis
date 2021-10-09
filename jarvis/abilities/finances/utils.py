from dataclasses import dataclass


@dataclass
class Expense:
    """
    This class represents an expense made by
    one of the people in a home.
    """
    price: int
    name: str
