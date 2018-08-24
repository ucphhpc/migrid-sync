from distutils.core import setup, Extension
setup(name='sslsession',
	version='0.1', \
	description='Module for extracting SSL session information',
	long_description='Module for extracting SSL session information',
	author='The MiG Project lead by Brian Vinter',
    author_email='NA',
    license='GPLv2',
    platforms=['Python 2.7'],
    url='https://sourceforge.net/projects/migrid/',
	ext_modules=[Extension('_sslsession', ['_sslsession.c'], include_dirs=['include'])])
