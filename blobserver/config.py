"Configuration."

import json
import os
import os.path

from blobserver import constants
from blobserver import utils

ROOT_DIRPATH = os.path.dirname(os.path.abspath(__file__))
SITE_DIRPATH = os.path.normpath(os.path.join(ROOT_DIRPATH, "../site"))

# Default configurable values; modified by reading a JSON file in 'init'.
DEFAULT_SETTINGS = dict(
    SERVER_NAME = "127.0.0.1:5009",   # For URL generation; app.run() in devel.
    SITE_NAME = "blobserver",
    SITE_ICON = None,           # Name of file in '../site' directory
    SITE_LOGO = None,           # Name of file in '../site' directory
    LOG_DEBUG = False,
    LOG_NAME = "blobserver",
    LOG_FILEPATH = None,
    LOG_ROTATING = 0,           # Number of backup rotated log files, if any.
    LOG_FORMAT = "%(levelname)-10s %(asctime)s %(message)s",
    JSON_AS_ASCII = False,
    JSON_SORT_KEYS = False,
    HOST_LOGO = None,           # Name of file in '../site' directory
    HOST_NAME = None,
    HOST_URL = None,
    CONTACT_EMAIL = None,
    SECRET_KEY = None,          # Must be set in 'settings.json'
    SALT_LENGTH = 12,
    STORAGE_DIRPATH = None,     # Must be set in 'settings.json'
    SQLITE3_FILENAME = "_data.sqlite3",    # Must start with underscore.
    MOST_RECENT = 40,
    MIN_PASSWORD_LENGTH = 6,
    PERMANENT_SESSION_LIFETIME = 7 * 24 * 60 * 60, # seconds; 1 week
    DEFAULT_QUOTA = 100000000,
    ADMIN_USERNAME = None,
    ADMIN_EMAIL = None,
    ADMIN_PASSWORD = None
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
    filepaths.append(os.path.join(ROOT_DIRPATH, "settings.json"))
    filepaths.append(os.path.join(SITE_DIRPATH, "settings.json"))
    for filepath in filepaths:
        try:
            app.config.from_file(filepath, load=json.load)
        except FileNotFoundError:
            pass
        else:
            app.config["SETTINGS_FILE"] = filepath
            break

    # Modify the configuration from environment variables.
    for key, default in DEFAULT_SETTINGS.items():
        try:
            value = os.environ[key] # Convert those that are not string.
            if isinstance(default, bool):
                value = utils.to_bool(value)
            elif isinstance(default, int):
                value = int(value)
        except (KeyError, TypeError, ValueError):
            pass
        else:
            app.config[key] = value

    # Clean up filepaths.
    for key in ["LOG_FILEPATH", "STORAGE_DIRPATH"]:
        path = app.config[key]
        if not path: continue
        path = os.path.expanduser(path)
        path = os.path.expandvars(path)
        path = os.path.normpath(path)
        path = os.path.abspath(path)
        app.config[key] = path

    # Sanity check; should not execute if this fails.
    if not app.config["SECRET_KEY"]:
        raise ValueError("SECRET_KEY must be set")
    if app.config["SALT_LENGTH"] <= 6:
        raise ValueError("SALT_LENGTH must be more than 6 characters")
    if app.config["MIN_PASSWORD_LENGTH"] <= 4:
        raise ValueError("MIN_PASSWORD_LENGTH must be more than 4 characters")
    if not app.config["STORAGE_DIRPATH"]:
        raise ValueError("STORAGE_DIRPATH has not been set")
    if not app.config["SQLITE3_FILENAME"]:
        raise ValueError("SQLITE3_FILEPATH has not been set")
    if not app.config["SQLITE3_FILENAME"].startswith("_"):
        raise ValueError("SQLITE3_FILEPATH must begin with underscore '_'")

    # Record dirpaths for access in app.
    app.config["ROOT_DIRPATH"] = ROOT_DIRPATH
    app.config["SITE_DIRPATH"] = SITE_DIRPATH
    app.config["SITE_STATIC_DIRPATH"] = os.path.join(SITE_DIRPATH, 'static')

    # Set the filepath for the Sqlite3 database.
    # Will always be in the storage directory,
    # but is protected by the beginning underscore.
    app.config["SQLITE3_FILEPATH"] = os.path.join(app.config["STORAGE_DIRPATH"],
                                                  app.config["SQLITE3_FILENAME"])
