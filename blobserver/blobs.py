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

@blueprint.route("/users")
def users():
    "List of number of blobs for the all users, and links to those lists."
    cursor = flask.g.db.cursor()
    rows = cursor.execute("SELECT username, COUNT(*) FROM blobs"
                          " GROUP BY username")
    users = [(blobserver.user.get_user(r[0]), r[1]) for r in rows]
    return flask.render_template("blobs/users.html", users=users)

@blueprint.route("/user/<username>")
def user(username):
    "List of all blobs for the given user."
    user = blobserver.user.get_user(username)
    if user is None:
        return utils.error("No such user.")
    cursor = flask.g.db.cursor()
    rows = cursor.execute("SELECT * FROM blobs WHERE username=?", (username,))
    blobs = [dict(zip(row.keys(), row)) for row in rows]
    return flask.render_template("blobs/user.html",
                                 user=user,
                                 blobs=blobs,
                                 commands=get_commands())

@blueprint.route("/search")
def search():
    "A very simple direct search of a single term."
    term = flask.request.args.get("term")
    if term:
        cursor = flask.g.db.cursor()
        wildterm = f"%{term}%"
        rows = cursor.execute("SELECT * FROM blobs WHERE filename LIKE ?"
                              " OR description LIKE ?", (wildterm, wildterm))
        blobs = [dict(zip(row.keys(), row)) for row in rows]
    else:
        blobs = []
    return flask.render_template("blobs/search.html", term=term, blobs=blobs)

def get_commands():
    if not flask.g.current_user: return None
    accesskey = flask.g.current_user.get("accesskey")
    if not accesskey: return None
    url = flask.url_for('blob.blob',
                        filename='blob-filename.ext',
                        _external=True)
    return {
        "curl": {
            "create": f'curl {url} -H "x-accesskey: {accesskey}"' \
            ' --upload-file path-to-content-file.ext'},
        "requests": {
            "create": f"""import requests

url = "{url}"
headers = {{"x-accesskey": "{accesskey}"}}
with open("path-to-content-file.ext", "rb") as infile:
    data = infile.read()

response = requests.put(url, headers=headers, data=data)
print(response.status_code)    # Outputs 200
"""}
    }
