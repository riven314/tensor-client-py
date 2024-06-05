class InvalidAPIKeyError(Exception):
    pass


class TensorServerOverloadError(Exception):
    pass


class UnknownAPIError(Exception):
    pass


class UnclassifiedStatusCodeError(Exception):
    pass
