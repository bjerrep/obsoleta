import logging, sys
from errorcodes import ErrorCode

indent = ''


class Indent():
    def __init__(self):
        global indent
        indent += '  '

    def __del__(self):
        global indent
        indent = indent[:-3]

    @staticmethod
    def indent():
        return indent


logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(indent + '%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

RESET = '\033[0m'
GREY = '\033[0;37m'
WHITE = '\033[1;37m'
LIGHT_GREEN = '\033[1;32m'
LIGHT_RED = '\033[1;31m'
LIGHT_RED2 = '\033[1;37;41m'

_GREY = GREY + '%3.3s'
_WHITE = WHITE + '%3.3s'
_LIGHT_GREEN = LIGHT_GREEN + '%3.3s'
_LIGHT_RED = LIGHT_RED + '%3.3s'
_LIGHT_RED2 = LIGHT_RED2 + '%3.3s'

logging.addLevelName(logging.DEBUG, _GREY % logging.getLevelName(logging.DEBUG))
logging.addLevelName(logging.INFO, _LIGHT_GREEN % logging.getLevelName(logging.INFO))
logging.addLevelName(logging.WARNING, _LIGHT_RED % logging.getLevelName(logging.WARNING))
logging.addLevelName(logging.ERROR, _LIGHT_RED2 % logging.getLevelName(logging.ERROR))
logging.addLevelName(logging.CRITICAL, _LIGHT_RED2 % logging.getLevelName(logging.CRITICAL))


def deb(msg):
    logger.debug(indent + msg)


def inf(msg, newline=True):
    if not newline:
        handler.terminator = ""
    logger.info(indent + msg)
    if not newline:
        handler.terminator = "\n"


def war(msg):
    logger.warning(indent + msg)


def err(msg):
    logger.error(indent + msg)


def cri(msg, exit_code):
    logger.critical(msg)
    logger.critical('error : ' + ErrorCode.to_string(exit_code.value))
    exit(exit_code.value)
