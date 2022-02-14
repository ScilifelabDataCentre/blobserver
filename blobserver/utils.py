"Various utility functions and classes."

import copy
import datetime
import functools
import html
import http.client
import json
import logging
import os.path
import sqlite3
import sys
import time
import uuid

import flask
import jinja2.utils
import marko
import werkzeug.routing

from blobserver import constants


def init(app):
    """Initialize app.
    - Add template filters.
    - Create the logs table in the database.
    """
    app.add_template_filter(markdown)
    app.add_template_filter(user_link)
    app.add_template_filter(tojson2)
    db = get_db(app)
    with db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS logs"
            "(iuid TEXT NOT NULL,"
            " diff TEXT NOT NULL,"
            " username TEXT,"
            " remote_addr TEXT,"
            " user_agent TEXT,"
            " timestamp TEXT NOT NULL)"
        )
        db.execute("CREATE INDEX IF NOT EXISTS" " logs_iuid_index ON logs (iuid)")


# Global logger instance.
_logger = None


def get_logger(app=None):
    global _logger
    if _logger is None:
        if app is None:
            app = flask.current_app
        config = app.config
        _logger = logging.getLogger(config["LOG_NAME"])
        if config["LOG_DEBUG"]:
            _logger.setLevel(logging.DEBUG)
        else:
            _logger.setLevel(logging.WARNING)
        if config["LOG_FILEPATH"]:
            if config["LOG_ROTATING"]:
                loghandler = logging.TimedRotatingFileHandler(
                    config["LOG_FILEPATH"],
                    when="midnight",
                    backupCount=config["LOG_ROTATING"],
                )
            else:
                loghandler = logging.FileHandler(config["LOG_FILEPATH"])
        else:
            loghandler = logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter(config["LOG_FORMAT"]))
        _logger.addHandler(loghandler)
    return _logger


def log_access(response):
    "Record access using the logger."
    if flask.g.current_user:
        username = flask.g.current_user["username"]
    else:
        username = None
    get_logger().debug(
        f"{flask.request.remote_addr} {username}"
        f" {flask.request.method} {flask.request.path}"
        f" {response.status_code}"
    )
    return response


# Decorators for endpoints
def login_required(f):
    "Decorator for checking if logged in. Send to login page if not."

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.current_user:
            url = flask.url_for("user.login", next=flask.request.base_url)
            return flask.redirect(url)
        return f(*args, **kwargs)

    return wrap


def admin_required(f):
    """Decorator for checking if logged in and 'admin' role.
    Otherwise return status 401 Unauthorized.
    """

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.am_admin:
            flask.abort(http.client.UNAUTHORIZED)
        return f(*args, **kwargs)

    return wrap


class IdentifierConverter(werkzeug.routing.BaseConverter):
    "URL route converter for an identifier."

    def to_python(self, value):
        if not constants.ID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value


class IuidConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a IUID."

    def to_python(self, value):
        if not constants.IUID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()  # Case-insensitive


class Timer:
    "CPU timer."

    def __init__(self):
        self.start = time.process_time()

    def __call__(self):
        "Return CPU time (in seconds) since start of this timer."
        return time.process_time() - self.start

    @property
    def milliseconds(self):
        "Return CPU time (in milliseconds) since start of this timer."
        return round(1000 * self())


def get_iuid():
    "Return a new IUID, which is a UUID4 pseudo-random string."
    return uuid.uuid4().hex


def to_bool(s):
    "Convert string value into boolean."
    if not s:
        return False
    s = s.lower()
    return s in ("true", "t", "yes", "y")


def get_time(offset=None):
    """Current date and time (UTC) in ISO format, with millisecond precision.
    Add the specified offset in seconds, if given.
    """
    instant = datetime.datetime.utcnow()
    if offset:
        instant += datetime.timedelta(seconds=offset)
    instant = instant.isoformat()
    return instant[:17] + "{:06.3f}".format(float(instant[17:])) + "Z"


def url_for(endpoint, **values):
    "Same as 'flask.url_for', but with '_external' set to True."
    return flask.url_for(endpoint, _external=True, **values)


def http_GET():
    "Is the HTTP method GET?"
    return flask.request.method == "GET"


def http_HEAD():
    "Is the HTTP method HEAD?"
    return flask.request.method == "HEAD"


def http_POST(csrf=True):
    "Is the HTTP method POST? Check whether used for method tunneling."
    if flask.request.method != "POST":
        return False
    if flask.request.form.get("_http_method") in (None, "POST"):
        if csrf:
            check_csrf_token()
        return True
    else:
        return False


def http_PUT():
    "Is the HTTP method PUT? Is not tunneled."
    return flask.request.method == "PUT"


def http_DELETE(csrf=True):
    "Is the HTTP method DELETE? Check for method tunneling."
    if flask.request.method == "DELETE":
        return True
    if flask.request.method == "POST":
        if csrf:
            check_csrf_token()
        return flask.request.form.get("_http_method") == "DELETE"
    else:
        return False


def csrf_token():
    "Output HTML for cross-site request forgery (CSRF) protection."
    # Generate a token to last the session's lifetime.
    if "_csrf_token" not in flask.session:
        flask.session["_csrf_token"] = get_iuid()
    html = (
        '<input type="hidden" name="_csrf_token" value="%s">'
        % flask.session["_csrf_token"]
    )
    return jinja2.utils.Markup(html)


def check_csrf_token():
    "Check the CSRF token for POST HTML."
    # Do not use up the token; keep it for the session's lifetime.
    token = flask.session.get("_csrf_token", None)
    if not token or token != flask.request.form.get("_csrf_token"):
        flask.abort(http.client.BAD_REQUEST)


def error(message, url=None):
    """ "Return redirect response to the given URL, or referrer, or home page.
    Flash the given message.
    """
    flash_error(message)
    return flask.redirect(url or referrer_or_home())


def referrer_or_home():
    "Return the URL for the referring page 'referer' or the home page."
    return flask.request.headers.get("referer") or flask.url_for("home")


def flash_error(msg):
    "Flash error message."
    flask.flash(str(msg), "error")


def flash_message(msg):
    "Flash information message."
    flask.flash(str(msg), "message")


def get_md_parser():
    "Get the Markdown parser for HTML. Allows for future extensions."
    return marko.Markdown()


def markdown(text):
    "Template filter to process the text using Marko markdown."
    text = html.escape(text or "", quote=False)
    return jinja2.utils.Markup(get_md_parser().convert(text))


def user_link(user):
    """Template filter for user output by name.
    Show as link to the user account page, if allowed.
    If 'blobs' is true, show as link to list of user's blobs.
    """
    from blobserver.user import am_admin_or_self

    if am_admin_or_self(user):
        url = flask.url_for("user.display", username=user["username"])
        return jinja2.utils.Markup(f'<a href="{url}">{user["username"]}</a>')
    else:
        return user["username"]


def tojson2(value, indent=2):
    """Transform to string JSON representation keeping single-quotes
    and indenting by 2 by default.
    """
    return json.dumps(value, indent=indent)


def get_db(app=None):
    "Get the connection to the Sqlite3 database file."
    if app is None:
        app = flask.current_app
    db = sqlite3.connect(app.config["SQLITE3_FILEPATH"])
    db.row_factory = sqlite3.Row
    return db


def get_logs(iuid):
    """Return the list of log entries for the given iuid,
    sorted by reverse timestamp.
    """
    cursor = flask.g.db.cursor()
    cursor.execute(
        "SELECT diff, username, remote_addr, user_agent, timestamp"
        " FROM logs WHERE iuid=?"
        " ORDER BY timestamp DESC",
        (iuid,),
    )
    result = []
    for row in cursor:
        item = dict(zip(row.keys(), row))
        item["diff"] = json.loads(item["diff"])
        result.append(item)
    return result


class BaseSaver:
    "Base entity saver context."

    LOG_EXCLUDE_PATHS = [["modified"]]  # Exclude from log info.
    LOG_HIDE_VALUE_PATHS = []  # Do not show value in log.

    def __init__(self, doc=None):
        if doc is None:
            self.original = {}
            self.doc = {}
            self.initialize()
        else:
            self.original = copy.deepcopy(doc)
            self.doc = doc
        self.prepare()

    def __enter__(self):
        return self

    def __exit__(self, etyp, einst, etb):
        if etyp is not None:
            return False
        self.finalize()
        self.doc["modified"] = get_time()
        self.upsert()
        self.add_log()

    def __getitem__(self, key):
        return self.doc[key]

    def __setitem__(self, key, value):
        self.doc[key] = value

    def initialize(self):
        "Initialize the new entity."
        self.doc["iuid"] = get_iuid()
        self.doc["created"] = get_time()

    def prepare(self):
        "Preparations before making any changes."
        pass

    def finalize(self):
        "Final operations and checks on the entity."
        pass

    def upsert(self):
        "Actually insert or update the entity in the database."
        raise NotImplementedError

    def add_log(self):
        """Add a log entry recording the the difference betweens the current
        and the original entity.
        """
        entry = {
            "iuid": self.doc["iuid"],
            "diff": json.dumps(self.diff(self.original, self.doc)),
            "timestamp": get_time(),
        }
        if hasattr(flask.g, "current_user") and flask.g.current_user:
            entry["username"] = flask.g.current_user["username"]
        if flask.has_request_context():
            entry["remote_addr"] = str(flask.request.remote_addr)
            entry["user_agent"] = str(flask.request.user_agent)
        else:
            entry["user_agent"] = os.path.basename(sys.argv[0])
        with flask.g.db:
            fields = ",".join([f"'{k}'" for k in entry.keys()])
            args = ",".join(["?"] * len(entry))
            flask.g.db.execute(
                f"INSERT INTO logs ({fields}) VALUES ({args})", list(entry.values())
            )

    def diff(self, old, new, stack=None):
        """Find the differences between the old and the new documents.
        Uses a fairly simple algorithm which is OK for shallow hierarchies.
        """
        if stack is None:
            stack = []
        added = {}
        removed = {}
        updated = {}
        new_keys = set(new.keys())
        old_keys = set(old.keys())
        for key in new_keys.difference(old_keys):
            stack.append(key)
            if stack not in self.LOG_EXCLUDE_PATHS:
                if stack in self.LOG_HIDE_VALUE_PATHS:
                    added[key] = "<hidden>"
                else:
                    added[key] = new[key]
            stack.pop()
        for key in old_keys.difference(new_keys):
            stack.append(key)
            if stack not in self.LOG_EXCLUDE_PATHS:
                if stack in self.LOG_HIDE_VALUE_PATHS:
                    removed[key] = "<hidden>"
                else:
                    removed[key] = old[key]
            stack.pop()
        for key in new_keys.intersection(old_keys):
            stack.append(key)
            if stack not in self.LOG_EXCLUDE_PATHS:
                new_value = new[key]
                old_value = old[key]
                if isinstance(new_value, dict) and isinstance(old_value, dict):
                    changes = self.diff(old_value, new_value, stack)
                    if changes:
                        if stack in self.LOG_HIDE_VALUE_PATHS:
                            updated[key] = "<hidden>"
                        else:
                            updated[key] = changes
                elif new_value != old_value:
                    if stack in self.LOG_HIDE_VALUE_PATHS:
                        updated[key] = dict(new_value="<hidden>", old_value="<hidden>")
                    else:
                        updated[key] = dict(new_value=new_value, old_value=old_value)
            stack.pop()
        result = {}
        if added:
            result["added"] = added
        if removed:
            result["removed"] = removed
        if updated:
            result["updated"] = updated
        return result
