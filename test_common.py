from common import ErrorCode
import subprocess


def test(a, b=True):
    if a != b:
        print('   assertion failed: %s != %s' % (str(a), str(b)))
        exit(ErrorCode.TEST_FAILED.value)


def title(serial, purpose):
    print()
    print('---------------------------------------------')
    print('Test ' + str(serial))
    print(purpose)
    print('---------------------------------------------')


def execute(command, expected_exit_code=0, quiet=False):
    global exit_code
    try:
        expected_exit_code = expected_exit_code.value
    except:
        pass

    try:
        if not quiet:
            print('executing "%s"' % command)
        output = None
        output = subprocess.check_output(command, shell=True)
        output = output.decode()
        if not quiet and output:
            print("%s" % output)
        if expected_exit_code != ErrorCode.OK.value:
            print('  process fail - didnt return exit code %i' % (expected_exit_code))
            exit_code = ErrorCode.TEST_FAILED
        return 0, output
    except subprocess.CalledProcessError as e:
        output = e.stdout.decode()
        if e.returncode != expected_exit_code:
            print('  process fail - unexpected exit code (not %i): %s' % (expected_exit_code, str(e)))
            exit_code = ErrorCode.TEST_FAILED
            exit(exit_code.value)
        else:
            print('  process pass with expected exit code %i %s' % (expected_exit_code, ErrorCode.to_string(expected_exit_code)))
        return e.returncode, output
