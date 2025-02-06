"Command-line interface to the blobserver instance."

import csv
import io
import os
import os.path
import tarfile
import time

import click
import flask

import blobserver.main
import blobserver.user

from blobserver import constants
from blobserver import utils


@click.group()
def cli():
    "Command-line interface to the blobserver instance."
    pass


@cli.command()
@click.option("--username", help="Username for the new admin account.", prompt=True)
@click.option("--email", help="Email address for the new admin account.", prompt=True)
@click.option(
    "--password",
    help="Password for the new admin account.",
    prompt=True,
    hide_input=True,
)
def create_admin(username, email, password):
    "Create a new admin account."
    with blobserver.main.app.app_context():
        flask.g.db = utils.get_db()
        try:
            with blobserver.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.ADMIN)
                saver.set_status(constants.ENABLED)
                saver.set_accesskey()
        except ValueError as error:
            raise click.ClickException(str(error))


@cli.command()
@click.option("--username", help="Username for the new user account.", prompt=True)
@click.option("--email", help="Email address for the new user account.", prompt=True)
@click.option(
    "--password",
    help="Password for the new user account.",
    prompt=True,
    hide_input=True,
)
def create_user(username, email, password):
    "Create a new user account."
    with blobserver.main.app.app_context():
        flask.g.db = utils.get_db()
        try:
            with blobserver.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.USER)
                saver.set_status(constants.ENABLED)
                saver.set_accesskey()
        except ValueError as error:
            raise click.ClickException(str(error))


@cli.command()
@click.option("--username", help="Username for the user account.", prompt=True)
@click.option(
    "--password",
    help="New password for the user account.",
    prompt=True,
    hide_input=True,
)
def password(username, password):
    "Set the password for a user account."
    with blobserver.main.app.app_context():
        flask.g.db = utils.get_db()
        user = blobserver.user.get_user(username=username)
        if user:
            with dbshare.user.UserSaver(user) as saver:
                saver.set_password(password)
        else:
            raise click.ClickException("No such user.")


@cli.command()
def users():
    "Output a CSV list of the user accounts."
    with blobserver.main.app.app_context():
        flask.g.db = utils.get_db()
        with io.StringIO() as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["username", "email", "role", "status", "accesskey"])
            for user in blobserver.user.get_users():
                writer.writerow(
                    [user["username"], user["email"], user["role"], user["status"], user["accesskey"]]
                )
            click.echo(outfile.getvalue())


@cli.command()
@click.option("--tarname", help="Name of the dump tar file.")
def dump(tarname):
    "Dump the database and all files to a '.tar.gz' dump file."
    with blobserver.main.app.app_context():
        if not tarname:
            tarname = "dump_{}.tar.gz".format(time.strftime("%Y-%m-%d"))
        if tarname.endswith(".gz"):
            mode = "w:gz"
        else:
            mode = "w"
        outfile = tarfile.open(tarname, mode=mode)
        dirpath = flask.current_app.config["STORAGE_DIRPATH"]
        count = 0
        size = 0
        for filename in os.listdir(dirpath):
            info = tarfile.TarInfo(filename)
            with open(os.path.join(dirpath, filename), "rb") as infile:
                data = infile.read()
            info.size = len(data)
            outfile.addfile(info, io.BytesIO(data))
            count += 1
            size += len(data)
        outfile.close()
        click.echo(f"Wrote {count} files, {size} bytes to {tarname}")


@cli.command()
@click.argument("input_tarfile", type=click.File("rb"))
def undump(input_tarfile):
    "Load a '.tar.gz' dump file; database and all files."
    with blobserver.main.app.app_context():
        # This unfortunately creates an empty master Sqlite3 file.
        flask.g.db = utils.get_db()
        if blobserver.user.get_users():
            raise click.ClickException("Cannot undump to a non-empty database.")
        with tarfile.open(fileobj=input_tarfile) as infile:
            # Check that the master Sqlite3 file exists.
            for item in infile:
                if item.name == flask.current_app.config["SQLITE3_FILENAME"]:
                    # Remove the just-created master Sqlite3 file.
                    flask.g.db.close()
                    os.remove(flask.current_app.config["SQLITE3_FILEPATH"])
                    break
            else:
                raise click.ClickException("No Sqlite3 master file in the dump file.")
            nitems = 0
            for item in infile:
                itemfile = infile.extractfile(item)
                itemdata = itemfile.read()
                itemfile.close()
                filepath = os.path.join(
                    flask.current_app.config["STORAGE_DIRPATH"], item.name
                )
                with open(filepath, "wb") as outfile:
                    outfile.write(itemdata)
                nitems += 1
        click.echo(f"{nitems} files in dump file.")


@cli.command()
@click.option("--username", help="Username to retrieve the access key for.", prompt=True)
def get_access_key(username):
    "Retrieve the access key for a given username."
    with blobserver.main.app.app_context():
        flask.g.db = utils.get_db()
        user = blobserver.user.get_user(username=username)
        if user:
            click.echo(user["accesskey"])
        else:
            raise click.ClickException("No such user.")


if __name__ == "__main__":
    cli()
