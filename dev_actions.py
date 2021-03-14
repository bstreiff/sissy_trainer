# Poetry doesn't have a command-sequencer, and running "poetry run <foo>" four times for
# different values of <foo> is really annoying, so wrap them up here.

import subprocess
import os

_MODULE = "sistrum"

def check():
    basedir = os.path.dirname(os.path.realpath(__file__))

    # Update docs
    subprocess.run(["make", "html"], cwd=os.path.join(basedir, "docs"))

    # Code coverage
    subprocess.run(["coverage", "run", "-m", "--source=" + _MODULE, "pytest"], cwd=basedir)
    subprocess.run(["coverage", "html"], cwd=basedir)
