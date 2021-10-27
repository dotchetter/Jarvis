
"""
This ability file holds intents related to
administrative intents in Jarvis.

Administrative intents include creating
database entries, changing settings, etc.
"""
from pyttman.core.intent import Intent


class CreateUserIntent(Intent):
    """
    The intent creates a database User instance
    for the provided data in message.author.

    Since platforms represent users differently,
    this uses whichever unique identifier provided
    by the platform and associates the identifier
    with the user.
    """
    def respond(self, message: Message) -> Union[Reply, ReplyStream]:
        pass
