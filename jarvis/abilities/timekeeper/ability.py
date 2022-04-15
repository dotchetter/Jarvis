from pyttman.core.ability import Ability

from jarvis.abilities.timekeeper.intents import StartStopWatch, StopStopWatch


class TimeKeeper(Ability):
    intents = (StartStopWatch,
               StopStopWatch)
