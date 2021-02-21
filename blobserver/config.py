"Configuration."

import os
import os.path

from blobserver import constants
from blobserver import utils

ROOT_DIRPATH = os.path.dirname(os.path.abspath(__file__))

# Default configurable values; modified by reading a JSON file in 'init'.
DEFAULT_SETTINGS = dict(
    SERVER_NAME = "127.0.0.1:5009",
    SITE_NAME = "blobserver",
    SITE_STATIC_DIRPATH = None,
    SITE_ICON = None,           # Filename, must be in 'SITE_STATIC_DIRPATH'
    SITE_LOGO = None,           # Filename, must be in 'SITE_STATIC_DIRPATH'
    DEBUG = False,
    LOG_DEBUG = False,
    LOG_NAME = "blobserver",
    LOG_FILEPATH = None,
    LOG_ROTATING = 0,           # Number of backup rotated log files, if any.
    LOG_FORMAT = "%(levelname)-10s %(asctime)s %(message)s",
    HOST_LOGO = None,           # Filename, must be in 'SITE_STATIC_DIRPATH'
    HOST_NAME = None,
    HOST_URL = None,
    SECRET_KEY = None,          # Must be set in 'settings.json'
    SALT_LENGTH = 12,
    STORAGE_DIRPATH = None,     # Must be set in 'settings.json'
    SQLITE3_FILENAME = "_data.sqlite3",    # Must start with underscore.
    JSON_AS_ASCII = False,
    JSON_SORT_KEYS = False,
    JSONIFY_PRETTYPRINT_REGULAR = False,
    MIN_PASSWORD_LENGTH = 6,
    PERMANENT_SESSION_LIFETIME = 7 * 24 * 60 * 60, # seconds; 1 week
    DEFAULT_QUOTA = 104857600,
    MAIL_SERVER = "localhost",
    MAIL_PORT = 25,
    MAIL_USE_TLS = False,
    MAIL_USERNAME = None,
    MAIL_PASSWORD = None,
    MAIL_DEFAULT_SENDER = None,
    USER_ENABLE_IMMEDIATELY = False,
    USER_ENABLE_EMAIL_WHITELIST = [], # List of fnmatch expressions
)

def init(app):
    """Perform the configuration of the Flask app.
    Set the defaults, and then read JSON settings file.
    Check the environment for a specific set of variables and use if defined.
    """
    # Set the defaults specified above.
    app.config.from_mapping(DEFAULT_SETTINGS)

    # Modify the configuration from a JSON settings file.
    try:
        filepaths = [os.environ["SETTINGS_FILEPATH"]]
    except KeyError:
        filepaths = []
    for filepath in ["settings.json", "../site/settings.json"]:
        filepaths.append(os.path.normpath(os.path.join(ROOT_DIRPATH, filepath)))
    for filepath in filepaths:
        try:
            app.config.from_json(filepath)
        except FileNotFoundError:
            pass
        else:
            app.config["SETTINGS_FILE"] = filepath
            break

    # Modify the configuration from environment variables.
    for key, convert in [("DEBUG", utils.to_bool),
                         ("SECRET_KEY", str),
                         ("COUCHDB_URL", str),
                         ("COUCHDB_USERNAME", str),
                         ("COUCHDB_PASSWORD", str),
                         ("MAIL_SERVER", str),
                         ("MAIL_USE_TLS", utils.to_bool),
                         ("MAIL_USERNAME", str),
                         ("MAIL_PASSWORD", str),
                         ("MAIL_DEFAULT_SENDER", str)]:
        try:
            app.config[key] = convert(os.environ[key])
        except (KeyError, TypeError, ValueError):
            pass

    # Clean up filepaths.
    for key in ["SITE_STATIC_DIRPATH", "LOG_FILEPATH", "STORAGE_DIRPATH"]:
        path = app.config[key]
        if not path: continue
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        path = os.path.normpath(path)
        path = os.path.abspath(path)
        app.config[key] = path

    # Sanity check; should not execute if this fails.
    assert app.config["SECRET_KEY"]
    assert app.config["SALT_LENGTH"] > 6
    assert app.config["MIN_PASSWORD_LENGTH"] > 4
    assert app.config["STORAGE_DIRPATH"]
    assert app.config["SQLITE3_FILENAME"]
    assert app.config["SQLITE3_FILENAME"].startswith("_")

    # Set the filepath for the Sqlite3 database.
    # Will always be in the storage directory,
    # but is protected by the beginning underscore.
    app.config["SQLITE3_FILEPATH"] = os.path.join(app.config["STORAGE_DIRPATH"],
                                                  app.config["SQLITE3_FILENAME"])
