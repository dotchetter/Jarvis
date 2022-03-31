from pyttman.core.communication.models.containers import Message


def extract_username(message: Message, entity_name: str) -> str:
    """
    Extracts the appropriate username depending on whether
        * it was mentioned in an Entity,
        * it's accessible on message.author.id (discord)
        * it's accessible on message.author (pyttman dev mode)
    """
    # Default to message.author.id unless provided as an entity
    if (username_for_query := message.entities.get(entity_name)) is None:
        username_for_query = get_username_from_message(message)
    return str(username_for_query)


def get_username_from_message(message: Message) -> str:
    try:
        username_for_query = message.author.id
    except AttributeError:
        username_for_query = message.author
    return username_for_query
