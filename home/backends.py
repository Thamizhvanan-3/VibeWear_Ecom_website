from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate with either the username or the email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        username = username.strip()
        try:
            user = UserModel._default_manager.filter(
                username__iexact=username
            ).first()
            if user is None and '@' in username:
                user = (
                    UserModel._default_manager.filter(email__iexact=username)
                    .exclude(email='')
                    .order_by('id')
                    .first()
                )
        except Exception:
            user = None

        if user is None:
            # Run the password hash once to reduce timing differences.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
