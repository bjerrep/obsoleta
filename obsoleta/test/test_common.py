import os, subprocess, shutil
from obsoleta.errorcodes import ErrorCode
from obsoleta.common import Error
from obsoleta.log import print_result, print_result_nl
from obsoleta.package import Package

OBSOLETA_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

TESTDATA_PATH = os.path.join(OBSOLETA_ROOT, 'obsoleta/test/testdata')

def test_eq(result, expected=True):
    if result != expected:
        print(f'assertion failed, got:\n{str(result)}\nexpected:\n{str(expected)}')
        print('\nTEST FAILED\n')
        exit(ErrorCode.TEST_FAILED.value)


def test_ok(error, output=None):
    if output:
        if isinstance(output, list):
            try:
                if isinstance(output, Package):
                    output = [p.to_string() for p in output]
                output = '\n'.join(output)
            except:
                output = ''
        print_result(output)
    if error.has_error():
        print_result_nl(f' - failed with "{error}"')
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
    if isinstance(errorcode, Error):
        errorcode = errorcode.get_errorcode()

    if errorcode != expected_error:
        print_result_nl('expected "%s" but got "%s"' %
                        (ErrorCode.to_string(errorcode.value),
                         ErrorCode.to_string(expected_error.value)))
    test_true(errorcode == expected_error, output)


def title(serial, purpose):
    print()
    print('---------------------------------------------')
    print(f'Test {str(serial)}')
    print(purpose)
    print('---------------------------------------------')


def execute(command, expected_exit_code=0, quiet=False, exitonerror=True):
    try:
        expected_exit_code = expected_exit_code.value
    except:
        pass

    if not quiet:
        print(f'executing "{command}"')

    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = proc.communicate()
    output = output.decode()

    if proc.returncode != expected_exit_code:
        print('  process fail - unexpected exit code %i (not %i)\n\n%s' %
              (proc.returncode, expected_exit_code, output))
        if exitonerror:
            print('terminating test with a fail since exitonerror=True')
            exit(proc.returncode)
        return proc.returncode, output

    if proc.returncode:
        print('  success, process failed with expected exit code %i\n\n%s' % (expected_exit_code, output))
        return proc.returncode, output

    if not quiet:
        print('  success')

    return proc.returncode, output


def populate_local_temp(src):
    shutil.rmtree('local/temp', True)
    shutil.copytree(os.path.join(f'{TESTDATA_PATH}/', src), 'local/temp')
    print(f'copy testdata from {src} to local/temp')
    return 'local/temp'
