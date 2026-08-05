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


class ChatPersistenceError(Exception):
    pass


class ChatPersistenceUncertainError(Exception):
    pass


class ChatRecordNotFoundError(Exception):
    pass


class InvalidChatQuestionError(Exception):
    pass
