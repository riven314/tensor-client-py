class InvalidAPIKeyError(Exception):
    pass


class TensorServerOverloadError(Exception):
    pass


class UnknownAPIError(Exception):
    pass


class UnclassifiedStatusCodeError(Exception):
    pass


class TransactionMissingError(Exception):
    pass


class BadRequestError(Exception):
    pass
