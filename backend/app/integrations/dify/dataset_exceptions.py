class DifyDatasetError(Exception):
    pass


class DifyDatasetConfigurationError(DifyDatasetError):
    pass


class DifyDatasetRequestError(DifyDatasetError):
    pass


class DifyDatasetUncertainError(DifyDatasetError):
    pass


class DifyDatasetInvalidResponseError(DifyDatasetError):
    pass
