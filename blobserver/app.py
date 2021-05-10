"Web app to upload and serve blobs (files)."

import flask
from flask_cors import CORS
import jinja2.utils

import blobserver.about
import blobserver.config
import blobserver.user
import blobserver.site
import blobserver.blob
import blobserver.blobs
from blobserver import constants
from blobserver import utils

app = flask.Flask(__name__)

CORS(app, supports_credentials=True)

# Add URL map converters.
app.url_map.converters["identifier"] = utils.IdentifierConverter
app.url_map.converters["iuid"] = utils.IuidConverter

# Get the configuration, and initialize modules (database).
blobserver.config.init(app)
utils.init(app)
blobserver.user.init(app)
blobserver.blob.init(app)

@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context of Jinja2 templates."
    return dict(constants=constants,
                csrf_token=utils.csrf_token,
                get_user=blobserver.user.get_user)

@app.before_first_request
def initialize():
    "Initialization before handling first request."
    blobserver.user.create_admin_user()

@app.before_request
def prepare():
    "Open the database connection; get the current user."
    flask.g.db = utils.get_db()
    flask.g.current_user = blobserver.user.get_current_user()
    flask.g.am_admin = flask.g.current_user and \
                       flask.g.current_user["role"] == constants.ADMIN

app.after_request(utils.log_access)

@app.route("/")
def home():
    "Home page."
    blobs = blobserver.blob.get_most_recent_blobs()
    return flask.render_template("home.html", blobs=blobs)

@app.route("/debug")
@utils.admin_required
def debug():
    "Return some debug info for admin."
    result = [f"<h1>Debug  {constants.VERSION}</h2>"]
    result.append("<h2>headers</h2>")
    result.append("<table>")
    for key, value in sorted(flask.request.headers.items()):
        result.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
    result.append("</table>")
    result.append("<h2>environ</h2>")
    result.append("<table>")
    for key, value in sorted(flask.request.environ.items()):
        result.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
    result.append("</table>")
    return jinja2.utils.Markup("\n".join(result))

@app.route("/status")
def status():
    "Return JSON for the current status and some counts for the database."
    cursor = flask.g.db.cursor()
    rows = list(cursor.execute("SELECT COUNT(*) FROM blobs"))
    n_blobs = rows[0][0]
    rows = list(cursor.execute("SELECT COUNT(*) FROM users"))
    n_users = rows[0][0]
    rows = list(cursor.execute("SELECT COUNT(*) FROM logs"))
    n_logs = rows[0][0]
    return dict(status="ok",
                n_blobs=n_blobs,
                n_users=n_users,
                n_logs=n_logs)

@app.route("/sitemap")
def sitemap():
    "Return an XML sitemap."
    cursor = flask.g.db.cursor()
    pages = [dict(url=flask.url_for("home", _external=True),
                  changefreq="daily",
                  priority=1.0),
             dict(url=flask.url_for("blobs.all", _external=True),
                  changefreq="daily",
                  priority=1.0),
             dict(url=flask.url_for("about.contact", _external=True),
                  changefreq="yearly"),
             dict(url=flask.url_for("about.software", _external=True),
                  changefreq="yearly")]
    rows = cursor.execute("SELECT filename FROM blobs")
    for row in rows:
        pages.append(
            dict(url=flask.url_for("blob.blob", filename=row["filename"], _external=True),
                 changefreq="weekly"))
        pages.append(
            dict(url=flask.url_for("blob.info", filename=row["filename"], _external=True),
                 changefreq="weekly"))
    pages.append(dict(url=flask.url_for("user.all", _external=True),
                      changefreq="monthly"))
    rows = cursor.execute("SELECT username FROM users")
    for row in rows:
        pages.append(
            dict(url=flask.url_for("user.display", username=row["username"], _external=True),
                 changefreq="weekly"))
    return flask.render_template("sitemap.xml", pages=pages)


# Set up the URL map.
app.register_blueprint(blobserver.about.blueprint, url_prefix="/about")
app.register_blueprint(blobserver.user.blueprint, url_prefix="/user")
app.register_blueprint(blobserver.site.blueprint, url_prefix="/site")
app.register_blueprint(blobserver.blob.blueprint, url_prefix="/blob")
app.register_blueprint(blobserver.blobs.blueprint, url_prefix="/blobs")


# This code is used only during development.
if __name__ == "__main__":
    app.run(host=app.config["SERVER_HOST"],
            port=app.config["SERVER_PORT"])
