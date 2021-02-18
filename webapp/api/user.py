"User display API endpoints."

import http.client

import flask

import webapp.user
from webapp import utils


blueprint = flask.Blueprint("api_user", __name__)

@blueprint.route("/")
def all():
    if not flask.g.am_admin:
        flask.abort(http.client.FORBIDDEN)
    users = [get_user_basic(u) for u in webapp.user.get_users()]
    return utils.jsonify(utils.get_json(users=users),
                         schema_url=utils.url_for("api_schema.users"))

@blueprint.route("/<identifier:username>")
def display(username):
    user = webapp.user.get_user(username=username)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    if not webapp.user.am_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    user.pop("password", None)
    user.pop("apikey", None)
    user["logs"] = {"href": utils.url_for(".logs", username=user["username"])}
    return utils.jsonify(utils.get_json(**user),
                         schema_url=utils.url_for("api_schema.user"))

@blueprint.route("/<identifier:username>/logs")
def logs(username):
    user = webapp.user.get_user(username=username)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    if not webapp.user.am_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    return utils.jsonify(utils.get_json(user=get_user_basic(user),
                                        logs=utils.get_logs(user["_id"])),
                         schema_url=utils.url_for("api_schema.logs"))

def get_user_basic(user):
    "Return the basic JSON data for a user."
    return {"username": user["username"],
            "href": utils.url_for(".display",username=user["username"])}
