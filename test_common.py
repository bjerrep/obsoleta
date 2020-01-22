from common import ErrorCode
from log import cri, print_result_nl
from package import Package
import subprocess


def test_eq(result, expected=True):
    if result != expected:
        print('   assertion failed: %s != %s' % (str(result), str(expected)))
        exit(ErrorCode.TEST_FAILED.value)


def test_success(success, output):
    if isinstance(output, list):
        try:
            if isinstance(output, Package):
                output = [p.to_string() for p in output]
            output = '\n'.join(output)
        except:
            output = ''
    cri(output) if not success else print_result_nl(output)
    print_result_nl('pass')


def title(serial, purpose):
    print()
    print('---------------------------------------------')
    print('Test ' + str(serial))
    print(purpose)
    print('---------------------------------------------')


def execute(command, expected_exit_code=0, quiet=False, exitonerror=True):
    global exit_code
    try:
        expected_exit_code = expected_exit_code.value
    except:
        pass

    if not quiet:
        print('executing "%s"' % command)

    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = proc.communicate()
    output = output.decode()

    if proc.returncode != expected_exit_code:
        print('  process fail - unexpected exit code %i (not %i)\n    %s' %
              (proc.returncode, expected_exit_code, output))
        if exitonerror:
            print('terminating test with a fail since exitonerror=True')
            exit(proc.returncode)
        return proc.returncode, output

    elif proc.returncode:
        print('  success, process failed with expected exit code %i\n    %s' % (expected_exit_code, output))
        return proc.returncode, output

    else:
        if not quiet:
            print('  success')

    return proc.returncode, output
