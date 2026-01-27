import os
import sys

# expose the configured environment as a constant
MIG_ENV = os.environ.get('MIG_ENV', 'local')

# force the chosen environment globally
os.environ['MIG_ENV'] = MIG_ENV
