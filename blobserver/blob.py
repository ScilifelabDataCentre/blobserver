"Blob display, serve and upload."

import hashlib

import flask

from blobserver import constants
from blobserver import utils
from blobserver.saver import BaseSaver

def init(app):
    "Initialize the database; create blob table."
    db = utils.get_db(app)
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS blobs"
                   "(filename TEXT PRIMARY KEY,"
                   " username TEXT NOT NULL,"
                   " description TEXT,"
                   " md5 TEXT NOT NULL,"
                   " sha256 TEXT NOT NULL,"
                   " sha512 TEXT NOT NULL,"
                   " created TEXT NOT NULL,"
                   " modified TEXT NOT NULL)")


blueprint = flask.Blueprint("blob", __name__)

@blueprint.route("/blob", methods=["GET", "POST"])
def upload():
    "Upload a new file."
    if utils.http_GET():
        return flask.render_template("blob/upload.html")

    elif utils.http_POST():
        pass


class BlobSaver(BaseSaver):
    "Save the blob (file)."

    DOCTYPE = 'blob'

    def finalize(self):
        for key in ["filename", "content", "user"]:
            if not self.doc.get(key):
                raise ValueError(f"Invalid blob: {key} not set.")

    def upsert(self):
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
        rows = list(cursor.execute("COUNT(*) FROM blobs WHERE filename=?",
                                   (self.doc["filename"],)))
        if rows[0][0] == 0:
            cursor.execute("INSERT INTO blobs ('filename', 'username',"
                           " 'description', 'md5', 'sha256', 'sha512')"
                           " VALUES (?, ?, ?, ?, ?, ?)",
                           (self.doc["filename"],
                            flask.g.current_user["username"],
                            self.doc.get("description"),
                            md5.hexdigest(),
                            sha256.hexdigest(),
                            sha512.hexdigest()))
        else:
            cursor.execute("UPDATE blobs SET (description=?, md5=?, sha256=?,"
                           " sha512=?) WHERE filename=?",
                           (self.doc.get("description"),
                            md5.hexdigest(),
                            sha256.hexdigest(),
                            sha512.hexdigest(),
                            self.doc["filename"]))


def get_blob_data(filename):
    """Return the data (not the content) for the blob.
    Return None if not found.
    """
    cursor = flask.g.db.cursor()
    rows = list(cursor.execute("SELECT filename, username, description,"
                               " md5, sha256, sha512, created, modified"
                               " FROM blobs WHERE filename=?",
                               (filename,)))
    if rows:
        return None
    else:
        return dict(zip(rows[0].keys(), rows[0]))
