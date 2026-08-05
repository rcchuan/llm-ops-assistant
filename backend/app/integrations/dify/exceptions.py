class DifyIntegrationError(Exception):
    pass


class DifyConfigurationError(DifyIntegrationError):
    pass


class DifyTimeoutError(DifyIntegrationError):
    pass


class DifyUnavailableError(DifyIntegrationError):
    pass


class DifyInvalidResponseError(DifyIntegrationError):
    pass
