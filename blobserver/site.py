"Site HTML endpoints."

import flask


blueprint = flask.Blueprint("site", __name__)

@blueprint.route("/static/<filename>")
def static(filename):
    "Static file for the site."
    return flask.send_from_directory(
        flask.current_app.config["SITE_STATIC"], filename)
