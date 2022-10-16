from pyttman.core.entity_parsing.identifiers import Identifier


class TimeStampIdentifier(Identifier):
    """
    Identifier for timestamps, e.g. "08:30"
    """
    patterns = (r"\d{2}:\d{2}",)
