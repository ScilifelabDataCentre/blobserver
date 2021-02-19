"Web app to upload and serve blobs (files)."

import flask
import jinja2.utils

import blobserver.about
import blobserver.config
import blobserver.user
import blobserver.site
import blobserver.blob

import blobserver.api.about
import blobserver.api.root
import blobserver.api.schema
import blobserver.api.user
# XXX To be developed.
# import blobserver.api.blob
from blobserver import constants
from blobserver import utils

app = flask.Flask(__name__)

# Add URL map converters.
app.url_map.converters["identifier"] = utils.IdentifierConverter
app.url_map.converters["iuid"] = utils.IuidConverter

# Get the configuration, and initialize modules (database).
blobserver.config.init(app)
utils.init(app)
blobserver.user.init(app)
blobserver.blob.init(app)
utils.mail.init_app(app)

@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context of Jinja2 templates."
    return dict(constants=constants,
                csrf_token=utils.csrf_token)

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
    "Home page. Redirect to API root if JSON is accepted."
    recent = blobserver.blob.get_most_recent_blobs()
    if utils.accept_json():
        return flask.redirect(flask.url_for("api_root"))
    else:
        return flask.render_template("home.html", recent=recent)

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

# Set up the URL map.
app.register_blueprint(blobserver.about.blueprint, url_prefix="/about")
app.register_blueprint(blobserver.user.blueprint, url_prefix="/user")
app.register_blueprint(blobserver.site.blueprint, url_prefix="/site")
app.register_blueprint(blobserver.blob.blueprint, url_prefix="/blob")

app.register_blueprint(blobserver.api.root.blueprint, url_prefix="/api")
app.register_blueprint(blobserver.api.about.blueprint, url_prefix="/api/about")
app.register_blueprint(blobserver.api.schema.blueprint, url_prefix="/api/schema")
app.register_blueprint(blobserver.api.user.blueprint, url_prefix="/api/user")
# XXX To be developed.
# app.register_blueprint(blobserver.api.blob.blueprint, url_prefix="/api/blob")


# This code is used only during development.
if __name__ == "__main__":
    app.run()
