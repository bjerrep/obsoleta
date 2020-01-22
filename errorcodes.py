from enum import Enum


class ErrorCode(Enum):
    OK = 0
    UNSET = 1
    INVALID_VERSION_NUMBER = 2
    PACKAGE_NOT_FOUND = 3
    ARCH_MISMATCH = 4
    MULTIPLE_VERSIONS = 5
    CIRCULAR_DEPENDENCY = 6
    TEST_FAILED = 7
    SYNTAX_ERROR = 8
    MISSING_INPUT = 9
    BAD_PATH = 10
    UNKNOWN_EXCEPTION = 11
    BAD_PACKAGE_FILE = 12
    DUPLICATE_PACKAGE = 13
    SLOT_ERROR = 14
    MULTISLOT_ERROR = 15
    MISSING_KEY_FILE = 16
    INVALID_KEY_FILE = 17
    COMPACT_PARSE_ERROR = 18
    OPTION_DISABLED = 19

    @staticmethod
    def to_string(errorcode):
        ErrorCodeToString = \
            ['Ok',
             'Unset',
             'Invalid version number',
             'Package not found',
             'Mixing different arch',
             'Multiple versions used',
             'Circular dependency',
             'Test failed',
             'Syntax error',
             'Missing input',
             'Bad path',
             'Unknown exception',
             'Bad package file',
             'Duplicate package',
             'Slot error',
             'Multislot error',
             'Missing key file',
             'Invalid key file',
             'Unable to parse compact name',
             'Option disabled'
             ]

        return ErrorCodeToString[errorcode]
