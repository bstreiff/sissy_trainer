# Poetry doesn't have a command-sequencer, and running "poetry run <foo>" four times for
# different values of <foo> is really annoying, so wrap them up here.

import subprocess
import os
import stat
import sys

_MODULE = "sistrum"

def check():
    basedir = os.path.dirname(os.path.realpath(__file__))

    e = subprocess.run(["black", "--check", _MODULE], cwd=basedir)
    if e.returncode != 0:
        sys.exit(e.returncode)

    # Run linter
    e = subprocess.run(["pylint", _MODULE], cwd=basedir)
    if e.returncode != 0:
        sys.exit(e.returncode)

    # Update docs
    e = subprocess.run(["make", "html"], cwd=os.path.join(basedir, "docs"))
    if e.returncode != 0:
        sys.exit(e.returncode)

    # Code coverage
    e = subprocess.run(["coverage", "run", "-m", "--source=" + _MODULE, "pytest"], cwd=basedir)
    if e.returncode != 0:
        sys.exit(e.returncode)
    e = subprocess.run(["coverage", "html"], cwd=basedir)
    if e.returncode != 0:
        sys.exit(e.returncode)


def pre_commit_hook():
    check()


def install_hooks():
    basedir = os.path.dirname(os.path.realpath(__file__))

    pre_commit_hook_str = r'''
#!/bin/sh

POETRY=$(which poetry)
if [ "$POETRY" = "" ]; then
	echo "*** Can't find poetry to invoke pre-commit hook!"
fi
if [ -e "$POETRY.bat" ]; then
	# On Windows, we want to run the .bat file sitting alongside.
	POETRY="$POETRY.bat"
fi

exec $POETRY run pre_commit_hook
'''.lstrip('\n')

    pre_commit_path = os.path.join(basedir, ".git", "hooks", "pre-commit")

    with open(pre_commit_path, "w") as fd:
        fd.write(pre_commit_hook_str)
    os.chmod(pre_commit_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
