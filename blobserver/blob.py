"Blob serve, information (metadata) display, upload and update."

import hashlib
import http.client
import os
import os.path

import flask

from blobserver import constants
from blobserver import utils

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
    "Upload a new blob via the web interface."
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
                saver["filename"] = infile.filename
                saver["description"] = flask.request.form.get("description")
                saver["username"] = flask.g.current_user["username"]
                saver.set_content(infile.read())
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(
            flask.url_for("blob.info", filename=saver["filename"]))

@blueprint.route("/<filename>", methods=["GET", "PUT", "DELETE"])
def blob(filename):
    """Return the blob itself.
    Programmatically create a new blob (PUT), update an existing blob (PUT),
    or delete an existing blob (DELETE).
    """
    if utils.http_GET() or utils.http_HEAD():
        data = get_blob_data(filename)
        if not data:
            # Just send error code; appropriate for programmatic use.
            flask.abort(http.client.NOT_FOUND)
        return flask.send_from_directory(
            flask.current_app.config["STORAGE_DIRPATH"], filename)

    elif utils.http_PUT():
        data = get_blob_data(filename)
        # Update an existing blob.
        if data:
            if not allow_update(data):
                flask.abort(http.client.UNAUTHORIZED)
            try:
                with BlobSaver(data) as saver:
                    saver.set_content(flask.request.data)
            except ValueError:
                flask.abort(http.client.BAD_REQUEST)
            return ("", http.client.OK)
        # Cannot create a new blob unless logged in.
        elif not flask.g.current_user:
            flask.abort(http.client.UNAUTHORIZED)
        # Create a new blob; the filename is part of the URL.
        else:
            try:
                with BlobSaver() as saver:
                    saver["filename"] = filename
                    saver.set_content(flask.request.data)
                    saver["username"] = flask.g.current_user["username"]
            except ValueError:
                flask.abort(http.client.BAD_REQUEST)
            return ("", http.client.CREATED)

    elif utils.http_DELETE():
        data = get_blob_data(filename)
        if not data:
            # Just send error code; appropriate for programmatic use.
            flask.abort(http.client.NOT_FOUND)
        if not allow_delete(data):
            # Just send error code; appropriate for programmatic use.
            flask.abort(http.client.FORBIDDEN)
        delete_blob(data)
        return ("", http.client.NO_CONTENT)

    flask.abort(http.client.METHOD_NOT_ALLOWED)

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
        return ("", http.client.OK)

    elif utils.http_DELETE():
        if not allow_delete(data):
            flask.abort(http.client.FORBIDDEN)
        try:
            with BlobSaver(data) as saver:
                saver["description"] = None
        except ValueError:
            flask.abort(http.client.BAD_REQUEST)
        return ("", http.client.OK)

    flask.abort(http.client.METHOD_NOT_ALLOWED)

@blueprint.route("/<filename>/info", methods=["GET", "POST", "DELETE"])
def info(filename):
    "Display the information about the blob. Delete from the web interface."
    data = get_blob_data(filename)
    if not data:
        return utils.error("No such blob.")

    if utils.http_GET():
        return flask.render_template("blob/info.html", 
                                     data=data,
                                     allow_update=allow_update(data),
                                     allow_delete=allow_delete(data),
                                     commands=get_commands(data))
    elif utils.http_DELETE():
        if not allow_delete(data):
            return utils.error("You are not allowed to delete the blob.")
        delete_blob(data)
        utils.flash_message(f"Deleted blob {data['filename']}")
        return flask.redirect(
            flask.url_for("blobs.user", username=data["username"]))

@blueprint.route("/<filename>/info.json")
def info_json(filename):
    "Return JSON of the information about the blob, including the log."
    data = get_blob_data(filename)
    if not data:
        flask.abort(http.client.NOT_FOUND)
    result = {"$id": flask.request.url,
              "href": flask.url_for("blob.blob", filename=filename, _external=True)}
    result.update(data)
    logs = utils.get_logs(data["iuid"])
    if not flask.g.current_user:
        # Remove half-insensitive data from logs: IP numbers and user agents.
        for log in logs:
            log.pop("remote_addr", None)
            log.pop("user_agent", None)
    result["logs"] = logs
    return flask.jsonify(result)

@blueprint.route("/<filename>/update", methods=["GET", "POST"])
@utils.login_required
def update(filename):
    "Update the content and/or the description of a blob."
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
            flask.url_for("blob.info", filename=saver["filename"]))

@blueprint.route("/<filename>/rename", methods=["GET", "POST"])
@utils.login_required
def rename(filename):
    data = get_blob_data(filename)
    if not data:
        return utils.error("No such blob.")
    if not allow_update(data):
        return utils.error("You may not rename the blob.")

    if utils.http_GET():
        return flask.render_template("blob/rename.html", data=data)

    elif utils.http_POST():
        try:
            with BlobSaver(data) as saver:
                saver.rename(flask.request.form.get("filename"))
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(
            flask.url_for("blob.info", filename=saver["filename"]))

@blueprint.route("/<filename>/copy", methods=["GET", "POST"])
@utils.login_required
def copy(filename):
    data = get_blob_data(filename)
    if not data:
        return utils.error("No such blob.")

    if utils.http_GET():
        return flask.render_template("blob/copy.html", data=data)

    elif utils.http_POST():
        filepath = os.path.join(flask.current_app.config['STORAGE_DIRPATH'],
                                data["filename"])
        try:
            with open(filepath, "rb") as infile:
                content = infile.read()
            with BlobSaver() as saver:
                saver["filename"] = flask.request.form.get("filename")
                saver["description"] = flask.request.form.get("description")
                saver["username"] = flask.g.current_user["username"]
                saver.set_content(content)
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(
            flask.url_for("blob.info", filename=saver["filename"]))

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


class BlobSaver(utils.BaseSaver):
    "Save the blob."

    LOG_EXCLUDE_PATHS = [["content"], ["modified"]]  # Exclude from log info.

    def set_content(self, content):
        self["content"] = content
        self["size"] = len(content)
        for name in ["md5", "sha256", "sha512"]:
            hash = hashlib.new(name)
            hash.update(content)
            self[name] = hash.hexdigest()

    def rename(self, filename):
        if filename.startswith("_"):
            raise ValueError("Filename is not allowed to start"
                             " with an underscore character.")
        if os.path.basename(filename) != filename:
            raise ValueError("Filename may not contain path specification.")
        cursor = flask.g.db.cursor()
        rows = list(cursor.execute("SELECT COUNT(*) FROM blobs WHERE filename=?",
                       (filename,)))
        if rows[0][0]:
            raise ValueError("A blob with the given filename already exists.")
        filepath = os.path.join(flask.current_app.config['STORAGE_DIRPATH'],
                                filename)
        if os.path.exists(filepath):
            raise ValueError("A file with the given filename already exists.")
        os.rename(os.path.join(flask.current_app.config['STORAGE_DIRPATH'],
                                self.doc["filename"]),
                  filepath)
        self["filename"] = filename

    def finalize(self):
        for key in ["filename", "username"]:
            if not self.doc.get(key):
                raise ValueError(f"Invalid blob: {key} not set.")
        if self.doc["filename"].startswith("_"):
            raise ValueError("Filename is not allowed to start"
                             " with an underscore character.")
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
            rows = list(cursor.execute("SELECT COUNT(*) FROM blobs WHERE"
                                       " iuid=?",
                                       (self.doc["iuid"],)))
            if rows[0][0] == 0:
                # Defensive paranoid check.
                if os.path.exists(filepath):
                    raise ValueError("Cannot overwrite existing non-blobserver"
                                     " file; use another filename.")
                keys = ["iuid", "filename", "username", "description", "md5",
                        "sha256", "sha512", "size", "modified", "created"]
                fields = ",".join(keys)
                args = ",".join(["?"] * len(keys))
                cursor.execute(f"INSERT INTO blobs ({fields}) VALUES ({args})",
                               [self.doc.get(k) for k in keys])
            else:
                keys = ["filename", "description", "md5",
                        "sha256", "sha512", "size", "modified"]
                assigns = ",".join([f"{k}=?" for k in keys])
                values = [self.doc.get(k) for k in keys] +[self.doc["iuid"]]
                cursor.execute(f"UPDATE blobs SET {assigns} WHERE iuid=?",
                               values)
            with open(filepath, "wb") as outfile:
                outfile.write(self.doc["content"])
        else:  # Filename or description has changed; only update is relevant.
            cursor.execute("UPDATE blobs SET filename=?, description=?"
                           " WHERE iuid=?",
                           (self.doc["filename"],
                            self.doc.get("description"),
                            self.doc["iuid"]))

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
        flask.g.db.execute("DELETE FROM logs WHERE iuid=?", (data["iuid"],))
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
    "Get commands and scripts populated with access key and URLs."
    if not flask.g.current_user: return None
    if not allow_update(data): return None
    accesskey = flask.g.current_user.get("accesskey")
    if not accesskey: return None
    content_url = flask.url_for('blob.blob',
                                filename=data['filename'],
                                _external=True)
    description_url = flask.url_for('blob.description',
                                    filename=data['filename'],
                                    _external=True)
    return {
        "curl": {
            "title": "curl commands",
            "text": """<strong>curl</strong> is a command-line utility to
transfer data to/from web servers. It is available for most computer operating
systems. See <a target="_blank" href="https://curl.se/">curl.se</a>.""",
            "content": f'curl {content_url} -H "x-accesskey: {accesskey}"' \
            ' --upload-file path-to-content-file.ext',
            "description": f'curl {description_url} -H "x-accesskey: {accesskey}"' \
            ' --upload-file path-to-description-file.md',
            "delete": f'curl {content_url} -H "x-accesskey: {accesskey}"' \
            " -X DELETE"},
        "python": {
            "title": "Python scripts using 'requests'",
            "text": """<strong>requests</strong> is a Python library for HTTP.
It is the <i>de facto</i> standard for Python. It must be downloaded from
<a target="_blank" href="https://pypi.org/project/requests/">PyPi</a>
since it is not part of the built-in Python libraries.
See <a target="_blank" href="https://requests.readthedocs.io/en/master/">
Requests: HTTP for Humans</a>.""",
            "content": f"""import requests

url = "{content_url}"
headers = {{"x-accesskey": "{accesskey}"}}
with open("path-to-content-file.ext", "rb") as infile:
    data = infile.read()

response = requests.put(url, headers=headers, data=data)
print(response.status_code)    # Outputs 200
""",
                "description": f"""import requests

url = "{description_url}"
headers = {{"x-accesskey": "{accesskey}"}}
with open("path-to-description-file.md", "rb") as infile:
    data = infile.read()

response = requests.put(url, headers=headers, data=data)
print(response.status_code)    # Outputs 200
""",
                "delete": f"""import requests

url = "{content_url}"
headers = {{"x-accesskey": "{accesskey}"}}
response = requests.delete(url, headers=headers)
print(response.status_code)    # Outputs 204
"""
        },
        "r": {
            "title": "R scripts",
            "text": """<strong>R</strong> is an open-source package for
statistics and data analysis available for most computer operating systems.
See <a target="_blank" href="https://www.r-project.org/">The R Project for
Statistical Computing</a>.""",
            "content": f"""install.packages(httr)
library(httr)

file_data <- upload_file("path-to-content-file.ext")
PUT("{content_url}",
    body = file_data,
    add_headers("x-accesskey"="{accesskey}"))
""",
            "description": f"""install.packages(httr)
library(httr)

file_data <- upload_file("path-to-content-file.ext")
PUT("{description_url}",
    body = file_data,
    add_headers("x-accesskey"="{accesskey}"))
""",
            "delete": f"""install.packages(httr)
library(httr)

DELETE("{content_url}",
       add_headers("x-accesskey"="{accesskey}"))
"""
        }
    }
