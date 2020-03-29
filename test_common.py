from errorcodes import ErrorCode
from log import print_result, print_result_nl
from package import Package
import subprocess, shutil


def test_eq(result, expected=True):
    if result != expected:
        print('   assertion failed: %s != %s' % (str(result), str(expected)))
        print('\nTEST FAILED\n')
        exit(ErrorCode.TEST_FAILED.value)


def test_ok(errorcode, output=None):
    if output:
        if isinstance(output, list):
            try:
                if isinstance(output, Package):
                    output = [p.to_string() for p in output]
                output = '\n'.join(output)
            except:
                output = ''
        print_result(output)
    if errorcode != ErrorCode.OK:
        print_result_nl(' - failed with "%s' % ErrorCode.to_string(errorcode.value))
        exit(1)
    else:
        print_result_nl(' - pass')


def test_true(success, output=None):
    if output:
        if isinstance(output, list):
            try:
                if isinstance(output, Package):
                    output = [p.to_string() for p in output]
                output = '\n'.join(output)
            except:
                output = ''
        print_result(output)
    if not success:
        print_result_nl(' - failed')
        exit(1)
    else:
        print_result_nl(' - pass')


def test_error(errorcode, expected_error, output=None):
    if errorcode != expected_error:
        print_result_nl('expected "%s" but got "%s"' %
                        (ErrorCode.to_string(errorcode.value),
                         ErrorCode.to_string(expected_error.value)))
    test_true(errorcode == expected_error, output)


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


def populate_local_temp(src):
    shutil.rmtree('local/temp', True)
    shutil.copytree(src, 'local/temp')
    return 'local/temp'
