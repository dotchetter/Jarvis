from pyttman.core.communication.models.containers import Message


def get_message_author_id(message: Message) -> str:
    """
    Helper function until Pyttman provides the .author
    attribute as an Author object, platform independent.

    :param message: Pyttman Message to parse
    :return: str
    """
    # Perform the query on the mentioned user, if present, else the author
    try:
        if message.mentions:
            author_id = message.mentions.pop().id
        else:
            author_id = message.author.id
    except AttributeError:
        author_id = message.author
    return author_id
