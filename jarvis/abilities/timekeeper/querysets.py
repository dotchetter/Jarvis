from datetime import datetime
import mongoengine as me
from jarvis.models import User


class ProjectQuerySet(me.QuerySet):
    """
    QuerySet class for the Project model
    """

    def try_get(self, *q_objs, default=None, **query):
        try:
            return super().get(*q_objs, **query)
        except me.DoesNotExist:
            return default

    def get_by_name_or_default_project(self, project_name: str, fallback=None):
        """
        Get the project which matches a name, or get the default
        project if no project matches the name.
        :param project_name: Name of the project to find
        :param fallback: What to return if no project matched name, and
               there is no default project
        """
        try:
            project_name = project_name.casefold()
        except AttributeError:
            project_name = ""

        if (project := self.try_get(name=project_name.casefold())) is None:
            project = self.filter(is_default=True).first()
        return project or fallback

    def get_active(self):
        """
        Get active projects
        """
        return self.filter(is_active=True).all()


class WorkShiftQuerySet(me.QuerySet):
    """
    QuerySet class for the WorkShift model
    """

    def get_all_for_user_in_current_month(self, user: User, **criterion):
        """
        Get all WorkShift objects which have occurred in the current
        month at the time of query, plus any additional criterion.
        :param user:
        :param criterion: Optional positional criterion arguments
        """
        return self.filter(
            user=user,
            month=datetime.now().month,
            year=datetime.now().year,
            **criterion
        ).all()

    def get_active_shift_for_user(self, user: User):
        """
        Get the currently active shift for a user
        """
        return self.filter(me.Q(user=user) & me.Q(is_active=True)).first()

    def get_for_today_for_user_and_project(self, user: User, project):
        """
        Get WorkShifts for today with a provided user and project
        """
        return self.filter(
            user=user,
            month=datetime.now().month,
            year=datetime.now().year,
            day=datetime.now().day,
            project=project
        ).all()
