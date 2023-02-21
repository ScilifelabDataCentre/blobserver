"User display and login/logout HTMl endpoints."

import flask
from werkzeug.security import check_password_hash, generate_password_hash

from blobserver import constants
from blobserver import utils

KEYS = [
    "iuid",
    "username",
    "email",
    "role",
    "status",
    "password",
    "accesskey",
    "quota",
    "created",
    "modified",
]


def init(app):
    "Initialize the database: create user table."
    db = utils.get_db(app)
    with db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS users"
            "(iuid TEXT PRIMARY KEY,"
            " username TEXT NOT NULL COLLATE NOCASE,"
            " email TEXT NOT NULL COLLATE NOCASE,"
            " role TEXT NOT NULL,"
            " status TEXT NOT NULL,"
            " password TEXT,"
            " accesskey TEXT,"
            " quota INTEGER,"
            " created TEXT NOT NULL,"
            " modified TEXT NOT NULL)"
        )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS"
            " users_username_index ON users (username)"
        )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS" " users_email_index ON users (email)"
        )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS"
            " users_accesskey_index ON users (accesskey)"
        )


blueprint = flask.Blueprint("user", __name__)


@blueprint.route("/login", methods=["GET", "POST"])
def login():
    "Login to a user account."
    if utils.http_GET():
        return flask.render_template("user/login.html")

    elif utils.http_POST():
        try:
            do_login(
                flask.request.form.get("username"), flask.request.form.get("password")
            )
        except ValueError:
            return utils.error(
                "Invalid user or password, or account disabled.",
                url=flask.url_for(".login"),
            )
        try:
            url = flask.session.pop("login_target_url")
        except KeyError:
            url = flask.url_for("home")
        return flask.redirect(url)


@blueprint.route("/logout", methods=["POST"])
def logout():
    "Logout from the user account."
    username = flask.session.pop("username", None)
    if username:
        utils.get_logger().info(f"logged out {username}")
    return flask.redirect(flask.url_for("home"))


@blueprint.route("/register", methods=["GET", "POST"])
@utils.admin_required
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
                saver.set_quota(flask.current_app.config["DEFAULT_QUOTA"])
                password = flask.request.form.get("password")
                confirm = flask.request.form.get("confirm_password")
                if password != confirm:
                    raise ValueError("Password confirmation failed.")
                saver.set_password(password)
                saver.set_status(constants.ENABLED)
            user = saver.doc
        except ValueError as error:
            return utils.error(error)
        utils.get_logger().info(f"registered user {user['username']}")
        return flask.redirect(flask.url_for("home"))


@blueprint.route("/password", methods=["GET", "POST"])
@utils.login_required
def password():
    "Set the password for a user account, and login user."
    if utils.http_GET():
        username = (
            flask.request.args.get("username") or flask.g.current_user["username"]
        )
        return flask.render_template("user/password.html", username=username)

    elif utils.http_POST():
        try:
            try:
                username = flask.request.form.get("username") or ""
                if not username:
                    raise ValueError
                user = get_user(username=username)
                if user is None:
                    raise ValueError
                if am_admin_and_not_self(user):
                    pass  # No check for current password.
                else:
                    password = flask.request.form.get("current_password") or ""
                    if not check_password_hash(user["password"], password):
                        raise ValueError
            except ValueError:
                raise ValueError("No such user or wrong password.")
            password = flask.request.form.get("password")
            if password != flask.request.form.get("confirm_password"):
                raise ValueError("Wrong password entered; confirm failed.")
        except ValueError as error:
            return utils.error(error, flask.url_for(".password"))
        with UserSaver(user) as saver:
            saver.set_password(password)
        utils.get_logger().info(f"password user {user['username']}")
        if not flask.g.current_user:
            do_login(username, password)
        return flask.redirect(flask.url_for("user.display", username=username))


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


@blueprint.route(
    "/display/<identifier:username>/edit", methods=["GET", "POST", "DELETE"]
)
@utils.login_required
def edit(username):
    "Edit the user display. Or delete the user."
    user = get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if not am_admin_or_self(user):
        return utils.error("Access not allowed.")

    if utils.http_GET():
        deletable = am_admin_and_not_self(user) and user["blobs_count"] == 0
        return flask.render_template(
            "user/edit.html",
            user=user,
            change_role=am_admin_and_not_self(user),
            deletable=deletable,
        )

    elif utils.http_POST():
        with UserSaver(user) as saver:
            if flask.g.am_admin:
                email = flask.request.form.get("email")
                if email != user["email"]:
                    saver.set_email(email)
                try:
                    quota = flask.request.form.get("quota") or None
                    if quota:
                        quota = int(quota)
                        if quota < 0:
                            raise ValueError
                except (ValueError, TypeError):
                    pass
                else:
                    saver.set_quota(quota)
            if am_admin_and_not_self(user):
                saver.set_role(flask.request.form.get("role"))
            if flask.request.form.get("accesskey"):
                saver.set_accesskey()
        return flask.redirect(flask.url_for(".display", username=user["username"]))

    elif utils.http_DELETE():
        if user["blobs_count"] != 0:
            return utils.error("Cannot delete non-empty user account.")
        with flask.g.db:
            flask.g.db.execute("DELETE FROM logs WHERE iuid=?", (user["iuid"],))
            flask.g.db.execute(
                "DELETE FROM users " " WHERE username=? COLLATE NOCASE", (username,)
            )
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
        logs=utils.get_logs(user["iuid"]),
    )


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
    if user["username"] == flask.g.current_user["username"]:
        return utils.error("You cannot enable yourself.")
    with UserSaver(user) as saver:
        saver.set_status(constants.ENABLED)
    utils.get_logger().info(f"enabled user {username}")
    return flask.redirect(flask.url_for(".display", username=username))


@blueprint.route("/disable/<identifier:username>", methods=["POST"])
@utils.admin_required
def disable(username):
    "Disable the given user account."
    user = get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if user["username"] == flask.g.current_user["username"]:
        return utils.error("You cannot disable yourself.")
    with UserSaver(user) as saver:
        saver.set_status(constants.DISABLED)
    utils.get_logger().info(f"disabled user {username}")
    return flask.redirect(flask.url_for(".display", username=username))


class UserSaver(utils.BaseSaver):
    "User document saver context."

    LOG_HIDE_VALUE_PATHS = [["password"], ["accesskey"]]

    def initialize(self):
        "Set the status and API key for a new user."
        super().initialize()
        self.set_status(constants.ENABLED)
        self.set_accesskey()

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

    def set_status(self, status):
        if status not in constants.USER_STATUSES:
            raise ValueError("Invalid status.")
        self.doc["status"] = status

    def set_role(self, role):
        if role not in constants.USER_ROLES:
            raise ValueError("Invalid role.")
        self.doc["role"] = role

    def set_quota(self, value=None):
        assert value is None or value >= 0
        self.doc["quota"] = value

    def set_password(self, password):
        "Set the password."
        if not password:
            raise ValueError("No password given.")
        if len(password) < flask.current_app.config["MIN_PASSWORD_LENGTH"]:
            raise ValueError("Password too short.")
        self.doc["password"] = generate_password_hash(
            password, salt_length=flask.current_app.config["SALT_LENGTH"]
        )

    def set_accesskey(self):
        "Set a new access key."
        self.doc["accesskey"] = utils.get_iuid()

    def upsert(self):
        "Actually insert or update the user in the database."
        # Cannot use the Sqlite3 native UPSERT: was included only in v 3.24.0
        cursor = flask.g.db.cursor()
        rows = list(
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE iuid=?", (self.doc["iuid"],)
            )
        )
        if rows[0][0] == 0:
            with flask.g.db:
                cursor.execute(
                    f"INSERT INTO users ({','.join(KEYS)})"
                    f" VALUES ({','.join('?'*len(KEYS))})",
                    [self.doc.get(k) for k in KEYS],
                )
        else:
            with flask.g.db:
                keys = KEYS[1:]  # Skip 'iuid'
                assignments = [f"{k}=?" for k in keys]
                values = [self.doc.get(k) for k in keys]
                values.append(self.doc["iuid"])
                cursor.execute(
                    "UPDATE users SET" f" {','.join(assignments)}" "WHERE iuid=?",
                    values,
                )


# Utility functions


def get_user(username=None, email=None, accesskey=None):
    """Return the user for the given username, email or accesskey.
    Return None if no such user.
    """
    sql = f"SELECT {','.join(KEYS)} FROM users"
    cursor = flask.g.db.cursor()
    if username:
        cursor.execute(sql + " WHERE username=? COLLATE NOCASE", (username,))
    elif email:
        cursor.execute(sql + " WHERE email=? COLLATE NOCASE", (email,))
    elif accesskey:
        cursor.execute(sql + " WHERE accesskey=?", (accesskey,))
    else:
        return None
    rows = list(cursor)
    if len(rows) == 0:
        return None
    else:
        user = dict(zip(rows[0].keys(), rows[0]))
        user["blobs_count"] = user_blobs_count(user)
        user["blobs_size"] = user_blobs_size(user)
        if user["quota"]:
            user["usage"] = round(100.0 * float(user["blobs_size"]) / user["quota"], 1)
        return user


def get_users(role=None, status=None):
    """Get the users optionally specified by role and status.
    Add total blobs count and size.
    """
    assert role is None or role in constants.USER_ROLES
    assert status is None or status in constants.USER_STATUSES
    cursor = flask.g.db.cursor()
    if role is None:
        rows = cursor.execute("SELECT * FROM users")
    elif status is None:
        rows = cursor.execute("SELECT * FROM users WHERE role=?", (role,))
    else:
        rows = cursor.execute(
            "SELECT * FROM users WHERE role=? AND status=?", (role, status)
        )
    users = [dict(zip(row.keys(), row)) for row in rows]
    for user in users:
        user["blobs_count"] = user_blobs_count(user)
        user["blobs_size"] = user_blobs_size(user)
    return users


def get_current_user():
    """Return the user for the current session.
    Return None if no such user, or disabled.
    """
    user = get_user(
        username=flask.session.get("username"),
        accesskey=flask.request.headers.get("x-accesskey"),
    )
    if user is None or user["status"] != constants.ENABLED:
        flask.session.pop("username", None)
        return None
    return user


def do_login(username, password):
    """Set the session cookie if successful login.
    Raise ValueError if some problem.
    """
    if not username:
        raise ValueError
    if not password:
        raise ValueError
    user = get_user(username=username)
    if user is None:
        raise ValueError
    if not check_password_hash(user["password"], password):
        raise ValueError
    if user["status"] != constants.ENABLED:
        raise ValueError
    flask.session["username"] = user["username"]
    flask.session.permanent = True
    utils.get_logger().info(f"logged in {user['username']}")


def am_admin_or_self(user):
    "Is the current user admin, or the same as the given user?"
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    return flask.g.current_user["username"] == user["username"]


def am_admin_and_not_self(user):
    "Is the current user admin and not the same as the given user?"
    if not flask.g.current_user:
        return False
    return flask.g.am_admin and flask.g.current_user["username"] != user["username"]


def user_blobs_count(user):
    "Return the number of blobs the user has."
    cursor = flask.g.db.cursor()
    rows = cursor.execute(
        "SELECT COUNT(*) FROM blobs WHERE username=?", (user["username"],)
    )
    return list(rows)[0][0] or 0


def user_blobs_size(user):
    "Return the total number of bytes for the blobs the user has."
    cursor = flask.g.db.cursor()
    rows = cursor.execute(
        "SELECT SUM(size) FROM blobs WHERE username=?", (user["username"],)
    )
    return list(rows)[0][0] or 0
