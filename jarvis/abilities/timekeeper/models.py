from datetime import datetime, timedelta, UTC
from datetime import time

import mongoengine as me

from jarvis.abilities.timekeeper.querysets import ProjectQuerySet, WorkShiftQuerySet
from jarvis.models import User


class Project(me.Document):
    """
    The Project model represents projects which workshifts
    relate to.
    """
    meta = {"queryset_class": ProjectQuerySet}
    name = me.StringField()
    is_active = me.BooleanField(default=False)
    is_default = me.BooleanField(default=False)
    created = me.DateTimeField(default=datetime.utcnow)
    hourly_rate = me.DecimalField(required=True)

    def __str__(self):
        return self.name.capitalize()

    @classmethod
    def all_project_names(cls) -> tuple[str]:
        """
        Get the raw property 'name' of all projects, as well
        as how they're presented in the application by __str__.
        """
        names = list(cls.objects.all().scalar("name"))
        presentable_names = [str(i) for i in cls.objects.all()]
        return tuple(names + presentable_names)


class WorkShift(me.Document):
    """
    the WorkShift model holds a period in time for a user.
    StopWatch instances have a beginning and an end.
    """
    meta = {"queryset_class": WorkShiftQuerySet}
    user = me.ReferenceField(User, required=True)
    beginning = me.DateTimeField(default=None, null=True)
    end = me.DateTimeField(default=None, null=True)
    is_active = me.BooleanField(default=True)
    is_consumed = me.BooleanField(default=False)
    created_at = me.DateTimeField(default=lambda: datetime.now())
    month = me.IntField(default=lambda: datetime.now().month)
    year = me.IntField(default=lambda: datetime.now().year)
    day = me.IntField(default=lambda: datetime.now().day)
    manually_created = me.BooleanField(default=False)
    project = me.ReferenceField(Project, required=False)

    @property
    def duration(self) -> time:
        _end = datetime.now() if self.end is None else self.end
        diff: timedelta = _end - self.beginning
        h = diff.seconds // 3600
        m = diff.seconds % 3600 // 60
        s = diff.seconds % 3600 % 60
        return time(h, m, s)

    def stop(self):
        """
        Stop the WorkShift, making this point in time the end marker
        of the life of this instance.
        """
        if self.is_active:
            self.end = datetime.now()
            self.is_active = False
            self.is_consumed = True
            self.save()

    def start(self):
        """
        Start the WorkShift, making this point in time the birth
        of this instance. Calling this method again will update the
        start point to that time point.
        Should the instance be consumed, meaning it was stopped already,
        an error is raised.

        :raise ValueError: When a consumed WorkShift which was already stopped
        is attempted to be started again, which is not allowed.
        """
        if self.is_consumed:
            raise ValueError("Cannot revive an old Workshift.")
        self.beginning = datetime.now()
        self.is_active = True
        self.save()
