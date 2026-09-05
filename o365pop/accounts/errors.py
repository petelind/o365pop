"""AUTH errors. Do not retry Celery on AuthenticationError (SAO §7)."""


class AuthenticationError(Exception):
    """Graph token login or refresh failed.

    :param message: Safe reason. Example: ``"refresh_token_rejected"``
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
