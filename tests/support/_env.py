import os
import sys

# expose the configured environment as a constant
MIG_ENV = os.environ.get('MIG_ENV', 'local')

# force the chosen environment globally
os.environ['MIG_ENV'] = MIG_ENV

# expose a boolean indicating whether we are executing on Python 2
PY2 = (sys.version_info[0] == 2)
