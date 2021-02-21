"Lists of blobs."

import flask

import blobserver.user
from blobserver import constants
from blobserver import utils

blueprint = flask.Blueprint("blobs", __name__)

@blueprint.route("/all")
def all():
    "List of all blobs."
    cursor = flask.g.db.cursor()
    rows = cursor.execute("SELECT * FROM blobs")
    blobs = [dict(zip(row.keys(), row)) for row in rows]
    return flask.render_template("blobs/all.html", blobs=blobs)

@blueprint.route("/user/<username>")
def user(username):
    "List of all blobs for the given user."
    user = blobserver.user.get_user(username)
    if user is None:
        return utils.error("No such user.")
    cursor = flask.g.db.cursor()
    rows = cursor.execute("SELECT * FROM blobs WHERE username=?", (username,))
    blobs = [dict(zip(row.keys(), row)) for row in rows]
    return flask.render_template("blobs/user.html", user=user, blobs=blobs)
