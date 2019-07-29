# IMPORTANT: do NOT update key once in production!
SECRET_KEY = "__SEAFILE_SECRET_KEY__"

# Uncomment next to enable debug mode
#DEBUG = True

# Site settings
# Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = '__SEAFILE_TIMEZONE__'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
# Default language for sending emails.
LANGUAGE_CODE = 'en'

# Set this to seahub website's URL. This URL is contained in email notifications.
SITE_BASE = 'https://__SEAFILE_FQDN__/seafile/'

# Set this to your website's name. This is contained in email notifications.
SITE_NAME = '__BASE_FQDN__'

# Set seahub website's title
SITE_TITLE = '__SHORT_TITLE__ Seafile'

# Address tweaks
# Use proxy URL
FILE_SERVER_ROOT = 'https://__SEAFILE_FQDN__/seafhttp'

# Use subdir address in vhost
SERVE_STATIC = False
MEDIA_URL = '/seafmedia/'
SITE_ROOT = '/seafile/'
LOGIN_URL = '/seafile/accounts/login/'    # NOTE: since version 5.0.4
COMPRESS_URL = MEDIA_URL
STATIC_URL = MEDIA_URL + 'assets/'

# Account settings
ENABLE_SIGNUP = True
# Require admin acceptance after signup
ACTIVATE_AFTER_REGISTRATION = False

# mininum length for password of encrypted library
REPO_PASSWORD_MIN_LENGTH = __PASSWORD_MIN_LEN__

# mininum length for user's password
USER_PASSWORD_MIN_LENGTH = __PASSWORD_MIN_LEN__

# LEVEL based on four types of input:
# num, upper letter, lower letter, other symbols
# '3' means password must have at least 3 types of the above.
USER_PASSWORD_STRENGTH_LEVEL = __PASSWORD_MIN_CLASSES__

# default False, only check USER_PASSWORD_MIN_LENGTH
# when True, check password strength level, STRONG(or above) is allowed
USER_STRONG_PASSWORD_REQUIRED = True

# Attempt limit before showing a captcha when login.
LOGIN_ATTEMPT_LIMIT = 3

# Whether a user's session cookie expires when the Web browser is closed.
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Anonymity options
# Enable cloud mode and hide `Organization` tab.
CLOUD_MODE = True
# Disable global address book
ENABLE_GLOBAL_ADDRESSBOOK = False

# DoS prevention
FILE_PREVIEW_MAX_SIZE = 30 * 1024 * 1024

# Email
EMAIL_USE_TLS = False
EMAIL_HOST = 'localhost'        # smpt server
EMAIL_HOST_USER = '__USER__@__BASE_FQDN__'    # username and domain
EMAIL_HOST_PASSWORD = ''    # password
EMAIL_PORT = '25'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER


# Seahub site customization in line with
# http://manual.seafile.com/config/seahub_customization.html
# Please note that the relative 'custom' folder should be symlinked to the
# seafile subfolder of the active MiG skin:
# 0|~ > cd ~/seafile/seafile-server-latest/seahub/media
# 0|.../seafile-server-latest/seahub/media > rm -f custom
# 0|.../seafile-server-latest/seahub/media > ln -s __MIG_CODE__/images/skin/__SKIN__/seafile custom
LOGO_PATH = 'custom/seafile_logo.png'
FAVICON_PATH = 'custom/favicon.png'
# Default width and height for logo is 149px and 32px
#LOGO_WIDTH = 149
#LOGO_HEIGHT = 32
BRANDING_CSS = 'custom/seahub.css'

# Enable WIKI by default
ENABLE_WIKI = True

# Enable optional 2FA for client logins
ENABLE_TWO_FACTOR_AUTH = __ENABLE_TWOFACTOR__
