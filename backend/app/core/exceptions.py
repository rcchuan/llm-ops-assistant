class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class UsernameAlreadyExistsError(Exception):
    pass


class OperatorOnlyOperationError(Exception):
    pass


class AuthenticationConfigurationError(Exception):
    pass


class PasswordChangeRequiredError(Exception):
    pass


class AdminRequiredError(Exception):
    pass
