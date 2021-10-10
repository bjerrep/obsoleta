import logging, sys
from errorcodes import ErrorCode

indent_string = ''


def indent():
    global indent_string
    indent_string += '  '


def unindent():
    global indent_string
    indent_string = indent_string[:-2]


def get_indent():
    global indent_string
    return indent_string


RESET = '\033[0m'

logger = logging.getLogger('obsoleta')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s %(message)s\033[0m')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)

if logging.getLevelName(logging.DEBUG) == 'DEBUG':
    # don't touch the level names if already done by someone else
    GREY = '\033[0;37m'
    WHITE = '\033[1;37m'
    LIGHT_GREEN = '\033[1;32m'
    LIGHT_RED = '\033[1;31m'
    LIGHT_RED2 = '\033[1;37;41m'

    logging.addLevelName(logging.DEBUG, GREY + '%3.3s' % logging.getLevelName(logging.DEBUG))
    logging.addLevelName(logging.INFO, LIGHT_GREEN + '%3.3s' % logging.getLevelName(logging.INFO))
    logging.addLevelName(logging.WARNING, LIGHT_RED + '%3.3s' % logging.getLevelName(logging.WARNING))
    logging.addLevelName(logging.ERROR, LIGHT_RED2 + '%3.3s' % logging.getLevelName(logging.ERROR))
    logging.addLevelName(logging.CRITICAL, LIGHT_RED2 + '%3.3s' % logging.getLevelName(logging.CRITICAL))


def get_info_log_level():
    return logger.level <= logging.INFO


def set_log_level(verbose=False, info=False):
    if verbose:
        logger.setLevel(logging.DEBUG)
    elif info:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.ERROR)


def deb(msg, newline=True):
    if not newline:
        handler.terminator = ""
    logger.debug(indent_string + msg)
    if not newline:
        handler.terminator = "\n"


def inf(msg, newline=True):
    if not newline:
        handler.terminator = ""
    logger.info(indent_string + msg)
    if not newline:
        handler.terminator = "\n"


def inf_alt(msg, newline=True):
    if not newline:
        handler.terminator = ""
    logger.info(indent_string + '\033[37m\033[44m' + msg)
    if not newline:
        handler.terminator = "\n"


def inf_alt2(msg, newline=True):
    if not newline:
        handler.terminator = ""
    logger.info(indent_string + '\033[37m\033[100m' + msg)
    if not newline:
        handler.terminator = "\n"


def war(msg):
    logger.warning(indent_string + msg)


def err(msg):
    logger.error(indent_string + msg)


def cri(msg, exit_code=ErrorCode.UNSET):
    logger.critical(msg)
    logger.critical('exit code : %i, %s' % (exit_code.value, ErrorCode.to_string(exit_code.value)))
    exit(exit_code.value)


def print_result(msg, newline=False):
    '''
    This should be used for printing results, no additional characters, no colors and
    default no newline.
    '''
    if newline:
        print(msg)
    else:
        print(msg, end='')


def print_result_nl(msg):
    print(msg)
