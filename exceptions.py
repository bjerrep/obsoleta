
from errorcodes import ErrorCode


class ObsoletaException(Exception):
    def __init__(self, msg, errorcode):
        super().__init__(msg)
        self.ErrorCode = errorcode


class BadPackageFile(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.BAD_PACKAGE_FILE)


class PackageNotFound(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.PACKAGE_NOT_FOUND)


class DuplicatePackage(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.DUPLICATE_PACKAGE)


class IllegalDependency(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.ILLEGAL_DEPENDENCY)


class MissingKeyFile(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.MISSING_KEY_FILE)


class InvalidKeyFile(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.INVALID_KEY_FILE)


class BadPath(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.BAD_PATH)


class CompactParseError(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.COMPACT_PARSE_ERROR)


class ModifyingReadonlyPackage(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.MODIFYING_READONLY_PACKAGE)


class UnknownException(ObsoletaException):
    def __init__(self, msg):
        super().__init__(msg, ErrorCode.UNKNOWN_EXCEPTION)
