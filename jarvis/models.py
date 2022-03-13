import mongoengine
from mongoengine import Document


class AppEnrollment(Document):
    """
    Embedded document, representing app names provided
    in Jarvis, allowing users to enroll and/or de-enroll from
    certain optional functionality in Jarvis.
    """
    shared_expenses = mongoengine.BooleanField(default=False)
    workshift = mongoengine.BooleanField(default=False)
