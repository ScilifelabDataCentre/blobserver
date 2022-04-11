"Command-line interface to the blobserver instance."

import csv
import io
import os
import tarfile
import time

import click
import flask

import blobserver.app
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
    with blobserver.app.app.app_context():
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
    with blobserver.app.app.app_context():
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
    with blobserver.app.app.app_context():
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
    with blobserver.app.app.app_context():
        flask.g.db = utils.get_db()
        with io.StringIO() as outfile:
            writer = csv.writer(outfile)
            writer.writerow(["username", "email", "role", "status"])
            for user in blobserver.user.get_users():
                writer.writerow([user["username"], user["email"], user["role"], user["status"]])
            click.echo(outfile.getvalue())

@cli.command()
@click.option("--tarname", help="Name of the dump tar file.")
def dump(tarname):
    with blobserver.app.app.app_context():
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
    with blobserver.app.app.app_context():
        # XXX check if data already exists; bail
        # How to replace the newly created db file?
        click.echo(f"undumping")


if __name__ == "__main__":
    cli()
