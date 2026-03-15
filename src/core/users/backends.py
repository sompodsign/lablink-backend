import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailOrUsernameBackend(ModelBackend):
    """Allow login with either username or email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # Try username first, then email
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                User().set_password(password)  # timing attack mitigation
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
