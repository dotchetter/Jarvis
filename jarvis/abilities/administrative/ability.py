
"""
This ability file holds intents related to
administrative intents in Jarvis.

Administrative intents include creating
database entries, changing settings, etc.
"""

from pyttman.core.ability import Ability
from jarvis.abilities.administrative.intents import *


class AdministrativeAbility(Ability):
    """
    Ability class for administrative intents in Jarvis
    """
    intents = (DevInfo, UserInfo, UserFeatureEnrollment)
