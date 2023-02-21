"blobserver: Web app to upload and serve blobs (files)."

import re
import os.path
import sys

__version__ = "1.3.0"


class Constants:
    def __setattr__(self, key, value):
        raise ValueError("Cannot set constant.")

    VERSION = __version__
    URL = "https://github.com/pekrau/blobserver"
    ROOT = os.path.dirname(os.path.abspath(__file__))
    SITE = os.path.normpath(os.path.join(ROOT, "../site"))

    PYTHON_VERSION = ".".join([str(i) for i in sys.version_info[0:3]])
    PYTHON_URL = "https://www.python.org/"

    FLASK_URL = "https://pypi.org/project/Flask/"
    JINJA2_URL = "https://pypi.org/project/Jinja2/"
    SQLITE3_URL = "https://www.sqlite.org/"
    MARKO_URL = "https://pypi.org/project/marko/"

    BOOTSTRAP_VERSION = "4.6.1"
    BOOTSTRAP_URL = "https://getbootstrap.com/"
    BOOTSTRAP_CSS_URL = (
        "https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/css/bootstrap.min.css"
    )
    BOOTSTRAP_CSS_INTEGRITY = (
        "sha384-zCbKRCUGaJDkqS1kPbPd7TveP5iyJE0EjAuZQTgFLD2ylzuqKfdKlfG/eSrtxUkn"
    )
    BOOTSTRAP_JS_URL = (
        "https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/js/bootstrap.bundle.min.js"
    )
    BOOTSTRAP_JS_INTEGRITY = (
        "sha384-fQybjgWLrvvRgtW6bFlB7jaZrFsaBXjsOMm/tB9LTS58ONXgqbR9W8oWht/amnpF"
    )

    JQUERY_VERSION = "3.5.1"
    JQUERY_URL = "https://jquery.com/"
    JQUERY_JS_URL = "https://code.jquery.com/jquery-3.5.1.slim.min.js"
    JQUERY_JS_INTEGRITY = (
        "sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj"
    )

    JQUERY_LOCALTIME_URL = "https://plugins.jquery.com/jquery.localtime/"
    JQUERY_LOCALTIME_VERSION = "0.9.1"
    JQUERY_LOCALTIME_FILENAME = "jquery.localtime-0.9.1.min.js"

    DATATABLES_VERSION = "1.10.24"
    DATATABLES_URL = "https://datatables.net/"
    DATATABLES_CSS_URL = (
        "https://cdn.datatables.net/1.10.24/css/dataTables.bootstrap4.min.css"
    )
    DATATABLES_JQUERY_JS_URL = (
        "https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"
    )
    DATATABLES_BOOTSTRAP_JS_URL = (
        "https://cdn.datatables.net/1.10.24/js/dataTables.bootstrap4.min.js"
    )

    CLIPBOARD_URL = "https://clipboardjs.com/"
    CLIPBOARD_VERSION = "2.0.6"
    CLIPBOARD_FILENAME = "clipboard.min.js"

    ID_RX = re.compile(r"^[a-z][a-z0-9_-]*$", re.I)
    IUID_RX = re.compile(r"^[a-f0-9]{32,32}$", re.I)
    EMAIL_RX = re.compile(r"^[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+$")

    # User roles
    ADMIN = "admin"
    USER = "user"
    USER_ROLES = (ADMIN, USER)

    # User statuses
    ENABLED = "enabled"
    DISABLED = "disabled"
    USER_STATUSES = [ENABLED, DISABLED]


constants = Constants()
