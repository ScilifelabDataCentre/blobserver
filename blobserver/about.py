"About info HTMl endpoints."

import sqlite3

import flask
import jinja2
import marko

from blobserver import constants
from blobserver import utils


blueprint = flask.Blueprint("about", __name__)

@blueprint.route("/software")
def software():
    "Show software versions."
    return flask.render_template("about/software.html",
                                 software=get_software())

def get_software():
    return [
        ("blobserver", constants.VERSION, constants.URL),
        ("Python", constants.PYTHON_VERSION, constants.PYTHON_URL),
        ('Flask', flask.__version__, constants.FLASK_URL),
        ('Jinja2', jinja2.__version__, constants.JINJA2_URL),
        ("Sqlite3", sqlite3.version, constants.SQLITE3_URL),
        ("Marko", marko.__version__, constants.MARKO_URL),
        ('Bootstrap', constants.BOOTSTRAP_VERSION, constants.BOOTSTRAP_URL),
        ('jQuery', constants.JQUERY_VERSION, constants.JQUERY_URL),
        ('jQuery.localtime', constants.JQUERY_LOCALTIME_VERSION, constants.JQUERY_LOCALTIME_URL),
        ('DataTables', constants.DATATABLES_VERSION, constants.DATATABLES_URL),
        ('clipboard.js', constants.CLIPBOARD_VERSION, constants.CLIPBOARD_URL),
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
