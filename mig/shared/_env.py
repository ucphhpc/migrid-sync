import os

MIG_BASE = os.path.realpath(os.path.join(os.path.dirname(__file__), '../..'))
MIG_ENV = os.getenv('MIG_ENV', 'default')
