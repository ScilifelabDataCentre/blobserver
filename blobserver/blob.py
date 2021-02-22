"Blob serve, metadata display, upload and update."

import hashlib
import http.client
import os
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


blueprint = flask.Blueprint("blob", __name__)

@blueprint.route("/", methods=["GET", "POST"])
@utils.login_required
def upload():
    "Upload a new blob."
    if utils.http_GET():
        return flask.render_template("blob/upload.html")

    elif utils.http_POST():
        infile = flask.request.files.get("file")
        if not infile:
            return utils.error("No file provided.")
        if get_blob_data(infile.filename):
            return utils.error("Blob already exists; do update instead.")
        try:
            with BlobSaver() as saver:
                saver["description"] = flask.request.form.get("description")
                saver["filename"] = infile.filename
                saver["username"] = flask.g.current_user["username"]
                saver.set_content(infile.read())
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(
            flask.url_for("blob.info", filename=saver["filename"]))

@blueprint.route("/<filename>", methods=["GET", "POST", "PUT", "DELETE"])
def blob(filename):
    if utils.http_GET() or utils.http_HEAD():
        data = get_blob_data(filename)
        if not data:
            # Just send error code; appropriate for programmatic use.
            flask.abort(http.client.NOT_FOUND)
        return flask.send_from_directory(
            flask.current_app.config["STORAGE_DIRPATH"], filename)

    elif utils.http_PUT():
        # Create a new blob; for programmatic use.
        data = get_blob_data(filename)
        if data:
            if not allow_update(data):
                flask.abort(http.client.UNAUTHORIZED)
            try:
                with BlobSaver(data) as saver:
                    saver.set_content(flask.request.data)
            except ValueError:
                flask.abort(http.client.BAD_REQUEST)
        elif not flask.g.current_user:
            flask.abort(http.client.UNAUTHORIZED)
        else:
            try:
                with BlobSaver() as saver:
                    saver["filename"] = filename
                    saver.set_content(flask.request.data)
                    saver["username"] = flask.g.current_user["username"]
            except ValueError:
                flask.abort(http.client.BAD_REQUEST)
        return flask.redirect(
            flask.url_for("blob.info", filename=saver["filename"]))

    elif utils.http_DELETE():
        data = get_blob_data(filename)
        if not data:
            # Just send error code; appropriate for programmatic use.
            flask.abort(http.client.NOT_FOUND)
        if not allow_delete(data):
            # Just send error code; appropriate for programmatic use.
            flask.abort(http.client.FORBIDDEN)
        delete_blob(data)
        utils.flash_message(f"Deleted blob {data['filename']}")
        return flask.redirect(
            flask.url_for("blobs.user", username=data["username"]))

    return flask.abort(http.client.METHOD_NOT_ALLOWED)

@blueprint.route("/<filename>/description", methods=["GET", "PUT", "DELETE"])
def description(filename):
    "Programmatic interface to the description for a blob."
    data = get_blob_data(filename)
    if not data:
        # Just send error code; appropriate for programmatic use.
        flask.abort(http.client.NOT_FOUND)

    if utils.http_GET() or utils.http_HEAD():
        response = flask.make_response(doc.get("description") or "")
        response.headers.set("Content-Type", "text/plain; charset=utf-8")
        return response

    elif utils.http_PUT():
        if not allow_update(data):
            flask.abort(http.client.FORBIDDEN)
        try:
            with BlobSaver(data) as saver:
                if flask.request.data:
                    saver["description"] = flask.request.data.decode('utf-8')
                else:
                    saver["description"] = None
        except ValueError:
            flask.abort(http.client.BAD_REQUEST)
        return flask.redirect(
            flask.url_for("blob.info", filename=saver["filename"]))

    elif utils.http_DELETE():
        if not allow_delete(data):
            flask.abort(http.client.FORBIDDEN)
        try:
            with BlobSaver(data) as saver:
                saver["description"] = None
        except ValueError:
            flask.abort(http.client.BAD_REQUEST)
        return flask.redirect(
            flask.url_for("blob.info", filename=saver["filename"]))

    return flask.abort(http.client.METHOD_NOT_ALLOWED)

@blueprint.route("/<filename>/info")
def info(filename):
    data = get_blob_data(filename)
    if not data:
        return utils.error("No such blob.")
    return flask.render_template("blob/info.html", 
                                 data=data,
                                 allow_update=allow_update(data),
                                 allow_delete=allow_delete(data),
                                 commands=get_commands(data))

@blueprint.route("/<filename>/update", methods=["GET", "POST"])
@utils.login_required
def update(filename):
    data = get_blob_data(filename)
    if not data:
        return utils.error("No such blob.")
    if not allow_update(data):
        return utils.error("You may not update the blob.")

    if utils.http_GET():
        return flask.render_template("blob/update.html", data=data)

    elif utils.http_POST():
        try:
            with BlobSaver(data) as saver:
                saver["description"] = flask.request.form.get("description")
                infile = flask.request.files.get("file")
                if infile:
                    saver.set_content(infile.read())
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(
            flask.url_for("blob.info", filename=data["filename"]))

@blueprint.route("/<filename>/logs")
def logs(filename):
    "Display the log records of the given blob."
    data = get_blob_data(filename)
    if not data:
        return utils.error("No such blob.")
    return flask.render_template(
        "logs.html",
        title=f"Blob {data['filename']}",
        cancel_url=flask.url_for(".info", filename=data["filename"]),
        logs=utils.get_logs(data["iuid"]))


class BlobSaver(BaseSaver):
    "Save the blob."

    LOG_EXCLUDE_PATHS = [["content"], ["modified"]]  # Exclude from log info.

    def set_content(self, content):
        self["content"] = content
        self["size"] = len(content)
        for name in ["md5", "sha256", "sha512"]:
            hash = hashlib.new(name)
            hash.update(content)
            self[name] = hash.hexdigest()

    def finalize(self):
        for key in ["filename", "username"]:
            if not self.doc.get(key):
                raise ValueError(f"Invalid blob: {key} not set.")
        if self.doc["filename"].startswith("_"):
            raise ValueError("Filename is not allowed to start with"
                             " an underscore character.")
        if flask.g.current_user["quota"]:
            if len(self.doc.get("content", [])) + \
               flask.g.current_user["blobs_size"] > \
               flask.g.current_user["quota"]:
                raise ValueError("User's quota cannot accommodate the blob.")

    def upsert(self):
        cursor = flask.g.db.cursor()
        if "content" in self.doc:  # The content has changed; insert or update.
            filepath = os.path.join(flask.current_app.config['STORAGE_DIRPATH'],
                                    self.doc["filename"])
            with open(filepath, "wb") as outfile:
                outfile.write(self.doc["content"])
            rows = list(cursor.execute("SELECT COUNT(*) FROM blobs WHERE"
                                       " filename=?",
                                       (self.doc["filename"],)))
            if rows[0][0] == 0:
                keys = ["iuid", "filename", "username", "description", "md5",
                        "sha256", "sha512", "size", "modified", "created"]
                fields = ",".join(keys)
                args = ",".join(["?"] * len(keys))
                cursor.execute(f"INSERT INTO blobs ({fields}) VALUES ({args})",
                               [self.doc.get(k) for k in keys])
            else:
                keys = ["description", "md5", "sha256", "sha512",
                        "size", "modified"]
                assigns = ",".join([f"{k}=?" for k in keys])
                values = [self.doc.get(k) for k in keys] +[self.doc["filename"]]
                cursor.execute(f"UPDATE blobs SET {assigns} WHERE filename=?",
                               values)
        else:  # Only the description has changed; only update is relevant.
            cursor.execute("UPDATE blobs SET description=? WHERE filename=?",
                           (self.doc.get("description"), self.doc["filename"]))

def get_blob_data(filename):
    """Return the data (not the content) for the blob.
    Return None if not found.
    """
    if filename.startswith("_"): return None
    cursor = flask.g.db.cursor()
    rows = list(cursor.execute("SELECT * FROM blobs WHERE filename=?",
                               (filename,)))
    if rows:
        return dict(zip(rows[0].keys(), rows[0]))
    else:
        return None

def get_most_recent_blobs():
    "Return the most recently modified blobs."
    cursor = flask.g.db.cursor()
    rows = list(cursor.execute("SELECT * FROM blobs"
                               " ORDER BY modified DESC LIMIT ?",
                               (flask.current_app.config["MOST_RECENT"],)))
    return [dict(zip(r.keys(), r)) for r in rows]

def delete_blob(data):
    "Delete the blob and its logs."
    with flask.g.db:
        flask.g.db.execute("DELETE FROM logs WHERE docid=?", (data["iuid"],))
        flask.g.db.execute("DELETE FROM blobs WHERE filename=?",
                           (data["filename"],))
        filepath = os.path.join(flask.current_app.config["STORAGE_DIRPATH"],
                                data["filename"])
        os.remove(filepath)

def allow_update(data):
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.current_user["username"] == data["username"]: return True
    return False

def allow_delete(data):
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.current_user["username"] == data["username"]: return True
    return False

def get_commands(data):
    if not flask.g.current_user: return None
    if not allow_update(data): return None
    accesskey = flask.g.current_user.get("accesskey")
    if not accesskey: return None
    c_url = flask.url_for('blob.blob',
                          filename=data['filename'],
                          _external=True)
    d_url = flask.url_for('blob.description',
                          filename=data['filename'],
                          _external=True)
    return {
        "curl": {
            "content": f'curl {c_url} -H "x-accesskey: {accesskey}"' \
            ' --upload-file path-to-content-file.ext',
            "description": f'curl {d_url} -H "x-accesskey: {accesskey}"' \
            ' --upload-file path-to-description-file.md',
            "delete": f'curl {c_url} -H "x-accesskey: {accesskey}"' \
            " -X DELETE"},
        "requests": {
            "content": f"""import requests

url = "{c_url}"
headers = {{"x-accesskey": "{accesskey}"}}
with open("path-to-content-file.ext", "rb") as infile:
    data = infile.read()

response = requests.put(url, headers=headers, data=data)
print(response.status_code)    # Outputs 200
""",
                "description": f"""import requests

url = "{d_url}"
headers = {{"x-accesskey": "{accesskey}"}}
with open("path-to-description-file.md", "rb") as infile:
    data = infile.read()

response = requests.put(url, headers=headers, data=data)
print(response.status_code)    # Outputs 200
""",
                "delete": f"""import requests

url = "{c_url}"
headers = {{"x-accesskey": "{accesskey}"}}
response = requests.delete(url, headers=headers)
print(response.status_code)    # Outputs 200
"""
        }
    }
