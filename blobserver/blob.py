"Blob serve, metadata display, upload and update."

import hashlib
import http.client
import os.path

import flask

from blobserver import constants
from blobserver import utils
from blobserver.saver import BaseSaver

def init(app):
    "Initialize the database; create blob table."
    db = utils.get_db(app)
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS blobs"
                   "(iuid TEXT PRIMARY KEY,"
                   " filename TEXT NOT NULL,"
                   " username TEXT NOT NULL,"
                   " description TEXT,"
                   " md5 TEXT NOT NULL,"
                   " sha256 TEXT NOT NULL,"
                   " sha512 TEXT NOT NULL,"
                   " size INTEGER NOT NULL,"
                   " created TEXT NOT NULL,"
                   " modified TEXT NOT NULL)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS"
                   " blobs_filename_index ON blobs (filename COLLATE NOCASE)")

KEYS = ["iuid", "filename", "username", "description",
        "md5", "sha256", "sha512", "size", "created", "modified"]


blueprint = flask.Blueprint("blob", __name__)

@blueprint.route("/", methods=["GET", "POST"])
@utils.login_required
def upload():
    "Upload a new blob."
    if utils.http_GET():
        return flask.render_template("blob/upload.html")

    elif utils.http_POST():
        infile = flask.request.files.get("blob")
        if not infile:
            return utils.error("No file provided.")
        if get_blob_data(infile.filename):
            return utils.error("Blob already exists; do update instead.")
        if infile.filename.startswith("_"):
            return utils.error("Filename is not allowed to start with an"
                               " underscore character; rename and try again.")
        with BlobSaver() as saver:
            saver["description"] = flask.request.form.get("description")
            saver["filename"] = infile.filename
            saver["content"] = infile.read()
            saver["username"] = flask.g.current_user["username"]
        return flask.redirect(flask.url_for("home"))

@blueprint.route("/<filename>", methods=["GET", "POST"])
def blob(filename):
    data = get_blob_data(filename)
    if not data:
        flask.abort(http.client.NOT_FOUND)
    return flask.send_from_directory(
        flask.current_app.config["STORAGE_DIRPATH"], filename)

@blueprint.route("/<filename>/details")
def details(filename):
    data = get_blob_data(filename)
    if not data:
        return utils.error("No such blob.")
    return flask.render_template("blob/details.html", data=data)


class BlobSaver(BaseSaver):
    "Save the blob."

    LOG_EXCLUDE_PATHS = [["content"], ["modified"]]  # Exclude from log info.

    def finalize(self):
        for key in ["filename", "content", "username"]:
            if not self.doc.get(key):
                raise ValueError(f"Invalid blob: {key} not set.")

    def upsert(self):
        if "content" in self.doc:  # The content has changed; insert or update.
            filepath = os.path.join(flask.current_app.config['STORAGE_DIRPATH'],
                                    self.doc["filename"])
            with open(filepath, "wb") as outfile:
                outfile.write(self.doc["content"])
            md5 = hashlib.new("md5")
            md5.update(self.doc["content"])
            sha256 = hashlib.new("sha256")
            sha256.update(self.doc["content"])
            sha512 = hashlib.new("sha512")
            sha512.update(self.doc["content"])
            cursor = flask.g.db.cursor()
            rows = list(cursor.execute("SELECT COUNT(*) FROM blobs WHERE"
                                       " filename=?",
                                       (self.doc["filename"],)))
            if rows[0][0] == 0:
                cursor.execute("INSERT INTO blobs ('filename', 'username',"
                               " 'description', 'md5', 'sha256', 'sha512',"
                               " 'size', 'modified', 'created')"
                               " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (self.doc["filename"],
                                flask.g.current_user["username"],
                                self.doc.get("description"),
                                md5.hexdigest(),
                                sha256.hexdigest(),
                                sha512.hexdigest(),
                                len(self.doc["content"]),
                                self.doc["modified"],
                                self.doc["created"]))
            else:
                cursor.execute("UPDATE blobs SET (description=?, md5=?,"
                               " sha256=?,sha512=?, size=?, modified=?)"
                               " WHERE filename=?",
                               (self.doc.get("description"),
                                md5.hexdigest(),
                                sha256.hexdigest(),
                                sha512.hexdigest(),
                                len(self.doc["content"]),
                                self.doc["filename"],
                                self.doc["modified"]))
        else:  # Only the description has changed; only update is relevant.
            cursor.execute("UPDATE blobs SET (description=?) WHERE filename=?",
                           (self.doc.get("description")))

def get_blob_data(filename):
    """Return the data (not the content) for the blob.
    Return None if not found.
    """
    if filename.startswith("_"): return None
    cursor = flask.g.db.cursor()
    rows = list(cursor.execute("SELECT iuid, filename, username, description,"
                               " md5, sha256, sha512, size, created, modified"
                               " FROM blobs WHERE filename=?",
                               (filename,)))
    if rows:
        return dict(zip(rows[0].keys(), rows[0]))
    else:
        return None

def get_most_recent_blobs():
    "Return the most recently modified blobs."
    cursor = flask.g.db.cursor()
    rows = list(cursor.execute("SELECT iuid, filename, username, description,"
                               " md5, sha256, sha512, size, created, modified"
                               " FROM blobs ORDER BY modified DESC"
                               " LIMIT ?",
                               (10,)))
    return [dict(zip(r.keys(), r)) for r in rows]
