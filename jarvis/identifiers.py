from pyttman.core.entity_parsing.identifiers import Identifier


class UrlIdentifier(Identifier):
    """
    Identifier for urls
    """
    patterns = ("http://", "https://", "www.")
