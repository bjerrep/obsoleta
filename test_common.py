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


def execute(command, expected_exit_code=0, quiet=False, exitonerror=True):
    global exit_code
    try:
        expected_exit_code = expected_exit_code.value
    except:
        pass

    if not quiet:
        print('executing "%s"' % command)

    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, stderr = proc.communicate()
    output = output.decode()
    stderr = stderr.decode()

    if proc.returncode != expected_exit_code:
        print('  process fail - unexpected exit code %i (not %i)\n    %s' %
              (proc.returncode, expected_exit_code, stderr))
        if exitonerror:
            print('terminating test with a fail since exitonerror=True')
            exit(proc.returncode)
        return proc.returncode, stderr

    elif proc.returncode:
        print('  success, process failed with expected exit code %i\n    %s' % (expected_exit_code, stderr))
        return proc.returncode, stderr

    else:
        if not quiet:
            print('  success')

    return proc.returncode, output
