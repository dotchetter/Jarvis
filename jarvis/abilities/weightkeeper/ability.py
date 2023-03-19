from pyttman.core.ability import Ability

from jarvis.abilities.weightkeeper.intents import EnterWeight


class WeightKeeper(Ability):
    """
    Ability for keeping track of the weight of the user.
    """
    intents = (EnterWeight,)
