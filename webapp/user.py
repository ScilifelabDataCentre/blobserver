"User display and login/logout HTMl endpoints."

import fnmatch
import http.client
import json

import flask
import flask_mail
from werkzeug.security import check_password_hash, generate_password_hash

from webapp import constants
from webapp import utils
from webapp.saver import BaseSaver

KEYS = ["iuid", "username", "email", "role", "status",
        "password", "apikey", "created", "modified"]

def init(app):
    "Initialize the database: create user table."
    db = utils.get_db(app)
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS users"
                   "(iuid TEXT PRIMARY KEY,"
                   " username TEXT NOT NULL,"
                   " email TEXT NOT NULL,"
                   " role TEXT NOT NULL,"
                   " status TEXT NOT NULL,"
                   " password TEXT,"
                   " apikey TEXT,"
                   " created TEXT NOT NULL,"
                   " modified TEXT NOT NULL)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS"
                   " users_username_index ON users (username COLLATE NOCASE)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS"
                   " users_email_index ON users (email COLLATE NOCASE)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS"
                   " users_apikey_index ON users (apikey)")

blueprint = flask.Blueprint("user", __name__)

@blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login to a user account.
    Creates the admin user specified in the settings.json, if not done.
    """
    if utils.http_GET():
        return flask.render_template("user/login.html",
                                     next=flask.request.args.get("next"))
    elif utils.http_POST():
        username = flask.request.form.get("username")
        password = flask.request.form.get("password")
        try:
            if username and password:
                do_login(username, password)
            else:
                raise ValueError
            try:
                next = flask.request.form["next"]
            except KeyError:
                return flask.redirect(flask.url_for("home"))
            else:
                return flask.redirect(next)
        except ValueError:
            return utils.error("Invalid user or password, or account disabled.")

@blueprint.route("/logout", methods=["POST"])
def logout():
    "Logout from the user account."
    username = flask.session.pop("username", None)
    if username:
        utils.get_logger().info(f"logged out {username}")
    return flask.redirect(flask.url_for("home"))

@blueprint.route("/register", methods=["GET", "POST"])
def register():
    "Register a new user account."
    if utils.http_GET():
        return flask.render_template("user/register.html")

    elif utils.http_POST():
        try:
            with UserSaver() as saver:
                saver.set_username(flask.request.form.get("username"))
                saver.set_email(flask.request.form.get("email"))
                saver.set_role(constants.USER)
                if flask.g.am_admin:
                    password = flask.request.form.get("password") or None
                    if password:
                        confirm = flask.request.form.get("confirm_password")
                        if password != confirm:
                            raise ValueError("Password differs from"
                                             " confirmed password.")
                    saver.set_password(password)
                    saver.set_status(constants.ENABLED)
                elif not flask.current_app.config["MAIL_SERVER"]:
                    password = flask.request.form.get("password") or None
                    if password:
                        confirm = flask.request.form.get("confirm_password")
                        if password != confirm:
                            raise ValueError("Password an confirmed password"
                                             " not the same.")
                    saver.set_password(password)
                else:
                    saver.set_password()
            user = saver.doc
        except ValueError as error:
            return utils.error(error)
        utils.get_logger().info(f"registered user {user['username']}")
        # Directly enabled.
        if user["status"] == constants.ENABLED:
            if user["password"][:5] == "code:":
                utils.get_logger().info(f"enabled user {user['username']}")
                # Send code by email to user.
                if flask.current_app.config["MAIL_SERVER"]:
                    send_password_code(user, "registration")
                    utils.flash_message("User account created; check your email.")
                # No email server: must contact admin.
                else:
                    utils.flash_message("User account created; contact"
                                        " the site admin to get the password"
                                        " setting code.")
            # Directly enabled and password set. No email to anyone.
            else:
                utils.get_logger().info(f"enabled user {user['username']}"
                                        " and set password")
                utils.flash_message("User account created and password set.")
        # Was set to 'pending'; send email to admins if email server defined.
        elif flask.current_app.config["MAIL_SERVER"]:
            admins = get_users(constants.ADMIN, status=constants.ENABLED)
            emails = [u["email"] for u in admins]
            site = flask.current_app.config["SITE_NAME"]
            message = flask_mail.Message(f"{site} user account pending",
                                         recipients=emails)
            url = utils.url_for(".display", username=user["username"])
            message.body = f"To enable the user account, go to {url}"
            utils.mail.send(message)
            utils.get_logger().info(f"pending user {user['username']}")
            utils.flash_message("User account created; an email will be sent"
                                " when it has been enabled by the admin.")
        else:
            utils.get_logger().info(f"pending user {user['username']}")
            utils.flash_message("User account created; admin will enable it"
                                " at some point. Try login later.")
        return flask.redirect(flask.url_for("home"))

@blueprint.route("/reset", methods=["GET", "POST"])
def reset():
    "Reset the password for a user account and send email."
    if not flask.current_app.config["MAIL_SERVER"]:
        return utils.error("Cannot reset password; no email server defined.")
        
    if utils.http_GET():
        email = flask.request.args.get("email") or ""
        email = email.lower()
        return flask.render_template("user/reset.html", email=email)

    elif utils.http_POST():
        try:
            user = get_user(email=flask.request.form["email"])
            if user is None: raise KeyError
            if user["status"] != constants.ENABLED: raise KeyError
        except KeyError:
            pass
        else:
            with UserSaver(user) as saver:
                saver.set_password()
            send_password_code(user, "password reset")
        utils.get_logger().info(f"reset user {user['username']}")
        utils.flash_message("An email has been sent if the user account exists.")
        return flask.redirect(flask.url_for("home"))

@blueprint.route("/password", methods=["GET", "POST"])
def password():
    "Set the password for a user account, and login user."
    if utils.http_GET():
        return flask.render_template(
            "user/password.html",
            username=flask.request.args.get("username"),
            code=flask.request.args.get("code"))

    elif utils.http_POST():
        try:
            code = ""
            try:
                username = flask.request.form.get("username") or ""
                if not username: raise ValueError
                user = get_user(username=username)
                if user is None: raise ValueError
                if am_admin_and_not_self(user):
                    pass        # No check for either code or current password.
                elif flask.current_app.config["MAIL_SERVER"]:
                    code = flask.request.form.get("code") or ""
                    if user["password"] != f"code:{code}": raise ValueError
                else:
                    password = flask.request.form.get("current_password") or ""
                    if not check_password_hash(user["password"], password):
                        raise ValueError
            except ValueError:
                if flask.current_app.config["MAIL_SERVER"]:
                    raise ValueError("No such user or wrong code.")
                else:
                    raise ValueError("No such user or wrong password.")
            password = flask.request.form.get("password") or ""
            if len(password) < flask.current_app.config["MIN_PASSWORD_LENGTH"]:
                raise ValueError("Too short password.")
            if not flask.current_app.config["MAIL_SERVER"]:
                if password != flask.request.form.get("confirm_password"):
                    raise ValueError("Wrong password entered; confirm failed.")
        except ValueError as error:
            return utils.error(error, flask.url_for(".password",
                                                    username=username,
                                                    code=code))
        with UserSaver(user) as saver:
            saver.set_password(password)
        utils.get_logger().info(f"password user {user['username']}")
        if not flask.g.current_user:
            do_login(username, password)
        return flask.redirect(flask.url_for("home"))

@blueprint.route("/display/<identifier:username>")
@utils.login_required
def display(username):
    "Display the given user."
    user = get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if not am_admin_or_self(user):
        return utils.error("Access not allowed.")
    return flask.render_template("user/display.html", user=user)

@blueprint.route("/display/<identifier:username>/edit",
                 methods=["GET", "POST", "DELETE"])
@utils.login_required
def edit(username):
    "Edit the user display. Or delete the user."
    user = get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if not am_admin_or_self(user):
        return utils.error("Access not allowed.")

    if utils.http_GET():
        deletable = am_admin_and_not_self(user) and is_empty(user)
        return flask.render_template("user/edit.html",
                                     user=user,
                                     change_role=am_admin_and_not_self(user),
                                     deletable=deletable)

    elif utils.http_POST():
        with UserSaver(user) as saver:
            if flask.g.am_admin:
                email = flask.request.form.get("email")
                if email != user["email"]:
                    saver.set_email(email)
            if am_admin_and_not_self(user):
                saver.set_role(flask.request.form.get("role"))
            if flask.request.form.get("apikey"):
                saver.set_apikey()
        return flask.redirect(
            flask.url_for(".display", username=user["username"]))

    elif utils.http_DELETE():
        if not is_empty(user):
            return utils.error("Cannot delete non-empty user account.")
        with flask.g.db:
            flask.g.db.execute("DELETE FROM logs WHERE docid=?",(user["iuid"],))
            flask.g.db.execute("DELETE FROM users "
                               " WHERE username=? COLLATE NOCASE",
                               (username,))
        utils.flash_message(f"Deleted user {username}.")
        utils.get_logger().info(f"deleted user {username}")
        if flask.g.am_admin:
            return flask.redirect(flask.url_for(".all"))
        else:
            return flask.redirect(flask.url_for("home"))

@blueprint.route("/display/<identifier:username>/logs")
@utils.login_required
def logs(username):
    "Display the log records of the given user."
    user = get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if not am_admin_or_self(user):
        return utils.error("Access not allowed.")
    return flask.render_template(
        "logs.html",
        title=f"User {user['username']}",
        cancel_url=flask.url_for(".display", username=user["username"]),
        api_logs_url=flask.url_for("api_user.logs", username=user["username"]),
        logs=utils.get_logs(user["iuid"]))

@blueprint.route("/all")
@utils.admin_required
def all():
    "Display list of all users."
    return flask.render_template("user/all.html", users=get_users())

@blueprint.route("/enable/<identifier:username>", methods=["POST"])
@utils.admin_required
def enable(username):
    "Enable the given user account."
    user = get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if user["username"].lower() == flask.g.current_user["username"].lower():
        return utils.error("You cannot enable yourself.")
    with UserSaver(user) as saver:
        saver.set_status(constants.ENABLED)
    if user["password"][:5] == "code:" and \
       flask.current_app.config["MAIL_SERVER"]:
        send_password_code(user, "enabled")
    utils.get_logger().info(f"enabled user {username}")
    return flask.redirect(flask.url_for(".display", username=username))

@blueprint.route("/disable/<identifier:username>", methods=["POST"])
@utils.admin_required
def disable(username):
    "Disable the given user account."
    user = get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if user["username"].lower() == flask.g.current_user["username"].lower():
        return utils.error("You cannot disable yourself.")
    with UserSaver(user) as saver:
        saver.set_status(constants.DISABLED)
    utils.get_logger().info(f"disabled user {username}")
    return flask.redirect(flask.url_for(".display", username=username))


class UserSaver(BaseSaver):
    "User document saver context."

    HIDDEN_VALUE_PATHS = [["password"]]

    def initialize(self):
        "Set the status for a new user."
        if flask.current_app.config["USER_ENABLE_IMMEDIATELY"]:
            self.doc["status"] = constants.ENABLED
        else:
            self.doc["status"] = constants.PENDING

    def finalize(self):
        "Check that required fields have been set."
        for key in ["username", "email", "role", "status"]:
            if not self.doc.get(key):
                raise ValueError(f"Invalid user: {key} not set.")

    def set_username(self, username):
        "Username can be set only when creating the account."
        if "username" in self.doc:
            raise ValueError("Username cannot be changed.")
        if not constants.ID_RX.match(username):
            raise ValueError("Invalid username; must be an identifier.")
        if get_user(username=username):
            raise ValueError("Username already in use.")
        self.doc["username"] = username

    def set_email(self, email):
        email = email.lower()
        if not constants.EMAIL_RX.match(email):
            raise ValueError("Invalid email.")
        if get_user(email=email):
            raise ValueError("Email already in use.")
        self.doc["email"] = email
        if self.doc.get("status") == constants.PENDING:
            for expr in flask.current_app.config["USER_ENABLE_EMAIL_WHITELIST"]:
                if fnmatch.fnmatch(email, expr):
                    self.set_status(constants.ENABLED)
                    break

    def set_status(self, status):
        if status not in constants.USER_STATUSES:
            raise ValueError("Invalid status.")
        self.doc["status"] = status

    def set_role(self, role):
        if role not in constants.USER_ROLES:
            raise ValueError("Invalid role.")
        self.doc["role"] = role

    def set_password(self, password=None):
        "Set the password; a one-time code if no password provided."
        config = flask.current_app.config
        if password is None:
            self.doc["password"] = "code:%s" % utils.get_iuid()
        else:
            if len(password) < config["MIN_PASSWORD_LENGTH"]:
                raise ValueError("Password too short.")
            self.doc["password"] = generate_password_hash(
                password, salt_length=config["SALT_LENGTH"])
            print("set password")

    def set_apikey(self):
        "Set a new API key."
        self.doc["apikey"] = utils.get_iuid()

    def upsert(self):
        "Actually insert or update the user in the database."
        # Cannot use the Sqlite3 native UPSERT: was included only in v 3.24.0
        cursor = flask.g.db.cursor()
        rows = list(cursor.execute("SELECT COUNT(*) FROM users WHERE iuid=?",
                                   (self.doc["iuid"],)))
        if rows[0][0] == 0:
            with flask.g.db:
                cursor.execute(f"INSERT INTO users ({','.join(KEYS)})"
                               f" VALUES ({','.join('?'*len(KEYS))})",
                               [self.doc.get(k) for k in KEYS])
        else:
            with flask.g.db:
                keys = KEYS[1:] # Skip 'iuid'
                assignments = [f"{k}=?" for k in keys]
                values = [self.doc.get(k) for k in keys]
                values.append(self.doc["iuid"])
                cursor.execute("UPDATE users SET"
                               f" {','.join(assignments)}"
                               "WHERE iuid=?", values)

# Utility functions

def get_user(username=None, email=None, apikey=None):
    """Return the user for the given username, email or apikey.
    Return None if no such user.
    """
    sql = f"SELECT {','.join(KEYS)} FROM users"
    cursor = flask.g.db.cursor()
    if username:
        cursor.execute(sql + " WHERE username=? COLLATE NOCASE", (username,))
    elif email:
        cursor.execute(sql + " WHERE email=? COLLATE NOCASE", (email,))
    elif apikey:
        cursor.execute(sql + " WHERE apikey=?", (apikey,))
    else:
        return None
    rows = list(cursor)
    if len(rows) == 0:
        return None
    else:
        return dict(zip(rows[0].keys(), rows[0]))

def get_users(role=None, status=None):
    "Get the users optionally specified by role and status."
    assert role is None or role in constants.USER_ROLES
    assert status is None or status in constants.USER_STATUSES
    cursor = flask.g.db.cursor()
    if role is None:
        rows = cursor.execute(f"SELECT {','.join(KEYS)} FROM users")
    elif status is None:
        rows = cursor.execute(f"SELECT {','.join(KEYS)} FROM users"
                              " WHERE role=?", (role,))
    else:
        rows = cursor.execute(f"SELECT {','.join(KEYS)} FROM users"
                              " WHERE role=? AND status=?", (role, status))
    return [dict(zip(row.keys(), row)) for row in rows]

def get_current_user():
    """Return the user for the current session.
    Return None if no such user, or disabled.
    """
    user = get_user(username=flask.session.get("username"),
                    apikey=flask.request.headers.get("x-apikey"))
    if user is None or user["status"] != constants.ENABLED:
        flask.session.pop("username", None)
        return None
    return user

def do_login(username, password):
    """Set the session cookie if successful login.
    Raise ValueError if some problem.
    """
    user = get_user(username=username)
    if user is None: raise ValueError
    if not check_password_hash(user["password"], password):
        raise ValueError
    if user["status"] != constants.ENABLED:
        raise ValueError
    flask.session["username"] = user["username"]
    flask.session.permanent = True
    utils.get_logger().info(f"logged in {user['username']}")

def send_password_code(user, action):
    "Send an email with the one-time code to the user's email address."
    site = flask.current_app.config["SITE_NAME"]
    message = flask_mail.Message(f"{site} user account {action}",
                                 recipients=[user["email"]])
    url = utils.url_for(".password",
                        username=user["username"],
                        code=user["password"][len("code:"):])
    message.body = f"To set your password, go to {url}"
    utils.mail.send(message)

def is_empty(user):
    "Is the given user account empty? No data associated with it."
    # XXX Needs implementation.
    return True

def am_admin_or_self(user):
    "Is the current user admin, or the same as the given user?"
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    return flask.g.current_user["username"].lower() == user["username"].lower()

def am_admin_and_not_self(user):
    "Is the current user admin, but not the same as the given user?"
    return flask.g.am_admin and \
        flask.g.current_user["username"].lower() != user["username"].lower()
