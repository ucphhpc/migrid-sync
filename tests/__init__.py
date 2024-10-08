def _print_identity():
    import os
    import sys
    python_version_string = sys.version.split(' ')[0]
    mig_env = os.environ.get('MIG_ENV', 'local')
    print("running with MIG_ENV='%s' under Python %s" %
          (mig_env, python_version_string))
    print("")

_print_identity()
