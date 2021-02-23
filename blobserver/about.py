"About info HTMl endpoints."

import sqlite3
import sys

import flask

import blobserver
from blobserver import constants
from blobserver import utils


blueprint = flask.Blueprint("about", __name__)

@blueprint.route("/software")
def software():
    "Show software versions."
    return flask.render_template("about/software.html",
                                 software=get_software())

def get_software():
    v = sys.version_info
    return [
        (constants.SOURCE_NAME, blobserver.__version__, constants.SOURCE_URL),
        ("Python", f"{v.major}.{v.minor}.{v.micro}", "https://www.python.org/"),
        ("Flask", flask.__version__, "http://flask.pocoo.org/"),
        ("Sqlite3", sqlite3.version, "https://www.sqlite.org/index.html"),
        ("Bootstrap", constants.BOOTSTRAP_VERSION, "https://getbootstrap.com/"),
        ("jQuery", constants.JQUERY_VERSION, "https://jquery.com/"),
        ("DataTables", constants.DATATABLES_VERSION, "https://datatables.net/"),
        ("clipboard.js", constants.CLIPBOARD_VERSION, "https://clipboardjs.com/")
    ]

@blueprint.route("/contact")
def contact():
    "Show contact information."
    return flask.render_template("about/contact.html")

@blueprint.route("/settings")
@utils.admin_required
def settings():
    config = flask.current_app.config.copy()
    for key in ["SECRET_KEY", "MAIL_PASSWORD"]:
        if config.get(key):
            config[key] = "<hidden>"
    return flask.render_template("about/settings.html",
                                 items=sorted(config.items()))
