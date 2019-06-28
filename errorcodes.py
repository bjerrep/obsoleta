from enum import Enum


class ErrorCode(Enum):
    OK = 0
    UNSET = 1
    SYSTEM_EXIT = 2
    PACKAGE_NOT_FOUND = 3
    ARCH_MISMATCH = 4
    MULTIPLE_VERSIONS = 5
    CIRCULAR_DEPENDENCY = 6
    TEST_FAILED = 7
    SYNTAX_ERROR = 8
    MISSING_INPUT = 9
    BAD_PATH = 10
    UNKNOWN_EXCEPTION = 11
    DEPENDENCY_NOT_FOUND = 12
    DUPLICATE_PACKAGE = 13
    SLOT_ERROR = 14
    MULTISLOT_ERROR = 15
    MISSING_KEY_FILE = 16
    INVALID_KEY_FILE = 17

    @staticmethod
    def to_string(errorcode):
        ErrorCodeToString = \
           ['Ok',
            'Unset',
            'System exit',
            'Package not found',
            'Mixing different arch',
            'Multiple versions',
            'Circular dependency',
            'Test failed',
            'Syntax error',
            'Missing input',
            'Bad path',
            'Unknown exception',
            'Dependency not found',
            'Duplicate package',
            'Slot error',
            'Multislot error',
            'Missing key file',
            'Invalid key file']

        return ErrorCodeToString[errorcode]
