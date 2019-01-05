from enum import Enum


class IllegalPackage(Exception):
    pass

class NoPackage(Exception):
    pass


class ErrorCode(Enum):
    OK = 0
    UNSET = 1
    DEPENDENCY_NOT_FOUND = 2
    PACKAGE_NOT_FOUND = 3
    ARCH_MISMATCH = 4
    MULTIPLE_VERSIONS = 5
    CIRCULAR_DEPENDENCY = 6
    TEST_FAILED = 7
    SYNTAX_ERROR = 8
    MISSING_INPUT = 9
    BAD_PATH = 10

    @staticmethod
    def to_string(errorcode):
        ErrorCodeToString = \
           ['Ok',
            'Unset',
            'Dependency not found',
            'Package not found',
            'Mixing different arch',
            'Multiple versions',
            'Circular dependency',
            'Test failed',
            'Syntax error',
            'Missing input',
            'Bad path']

        return ErrorCodeToString[errorcode]


class Error:
    def __init__(self, error_type, package, message=''):
        self.error_type = error_type
        self.package = package
        if message:
            self.message = message
        elif package.parent:
            self.message = 'from parent ' + package.parent.to_string()
        else:
            self.message = ''

    def get_error(self):
        return self.error_type

    def __str__(self):
        return ErrorCode.to_string(self.error_type.value) + ': ' + self.package.to_string()

    def to_string(self):
        return ErrorCode.to_string(self.error_type.value) + ': ' + self.package.to_string() + ' ' + str(self.message)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        uid = str(self)
        return hash(uid)
