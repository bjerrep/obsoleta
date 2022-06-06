import shutil, os, subprocess

""" PYSCRIPT
pyscript is trying to bridge the simplicity of small bash scripts with the power of Python.
Its absolute only goal is to help making small scripts quicker to write and easier to maintain.

A pyscript should require a minimum of development effort and ideally offer no surprises.
pyscript can not beat a few lines of bash and it would be completely out of place in regular python importing
modules left and right and doing fancy stuff. But it can quickly be a competitor to e.g. bash scripts once
they start to get littered with loops and tests with names that have to be looked up and then doesn't work
because there is a missing space and then explodes if a variable is empty, and so on and so on.

pyscript has only been tested in single user plain filesystems and there is no reason to believe
that it wont fail misserably in non-plain filesystems.
"""


def deb(message):
    print(f'DEB{message}')


def err(message):
    print(f'ERR{message}')


def die(message, exitcode):
    print(f'DIE {message} (exitcode={exitcode})')
    os._exit(exitcode)


def file_del(filename):
    """ Delete file, ignore any errors.
    """
    try:
        deb('removing file %s' % filename)
        os.remove(filename)
    except:
        err('removing file %s failed' % filename)


pushed_dir = ''


def dir_cd(directory):
    """ Change directory, save current location in a one deep stack (see dir_pop())
    """
    global pushed_dir
    deb('chdir %s' % directory)
    pushed_dir = os.getcwd()
    os.chdir(directory)


def dir_pop():
    """ Change directory from pop from one deep stack (see dir_cd())
    """
    global pushed_dir
    deb('pop directory %s' % pushed_dir)
    os.chdir(pushed_dir)
    pushed_dir = ''


def dir_del(directory):
    """ Delete directory, ignore any errors.
    """
    try:
        deb('deleting directory %s' % directory)
        shutil.rmtree(directory, True)
    except:
        err('deleting directory %s failed' % directory)


def dir_construct(directory):
    try:
        deb('constructing directory %s' % directory)
        os.makedirs(directory)
    except:
        pass


def dir_copy_rewrite(source, destination):
    """ Delete the destination directory if it exists, then make the copy.
    """
    dir_del(destination)
    deb('copying directory %s to %s' % (source, destination))
    shutil.copytree(source, destination)


def run(command, directory='.', autoexit=False):
    """ Execute commmand with subprocess, printing stdout and stderr in
        realtime (nice for long running commands).
        If directory is given then the command is executed from there.
        If autoexit is True then a hard exit is made if the command gives
        a non zero exit code.
        Return: (exitcode, stdout as list of lines)
    """
    deb('running command "%s" in "%s"' % (command, directory))
    if directory != '.':
        cur = os.getcwd()
        os.chdir(directory)

    output = []
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        line = p.stdout.readline().decode("utf-8")
        if line == '' and p.poll() is not None:
            break
        line = line.rstrip()
        print(line)
        output.append(line)

    if directory != '.':
        os.chdir(cur)

    if autoexit and p.returncode:
        die('run command %s failed' % command, p.returncode)

    if len(output) > 0 and not output[-1]:
        output = output[:-1]
    return p.returncode, output
