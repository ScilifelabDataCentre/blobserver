"Web app template based on Flask and Sqlite3. With user account handling."

import re

__version__ = "0.3.1"

class Constants:
    VERSION     = __version__
    SOURCE_NAME = "blobserver"
    SOURCE_URL  = "https://github.com/pekrau/blobserver"

    BOOTSTRAP_VERSION  = "4.6.0"
    JQUERY_VERSION     = "3.5.1"
    DATATABLES_VERSION = "1.10.23"

    ID_RX    = re.compile(r"^[a-z][a-z0-9_-]*$", re.I)
    IUID_RX  = re.compile(r"^[a-f0-9]{32,32}$", re.I)
    EMAIL_RX = re.compile(r"^[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+$")

    # User roles
    ADMIN = "admin"
    USER  = "user"
    USER_ROLES = (ADMIN, USER)

    # User statuses
    PENDING  = "pending"
    ENABLED  = "enabled"
    DISABLED = "disabled"
    USER_STATUSES = [PENDING, ENABLED, DISABLED]

    def __setattr__(self, key, value):
        raise ValueError("Cannot set constant.")


constants = Constants()