"Command-line interface."

import argparse
import getpass
import io
import os
import sys
import tarfile
import time

import flask

import blobserver.app
import blobserver.user

from blobserver import constants
from blobserver import utils


def get_parser():
    "Get the parser for the command line interface."
    p = argparse.ArgumentParser(
        prog="cli.py",
        usage="python %(prog)s [options]",
        description="blobserver command line interface",
    )
    p.add_argument("-d", "--debug", action="store_true", help="Debug logging output.")
    x0 = p.add_mutually_exclusive_group()
    x0.add_argument(
        "-A", "--create_admin", action="store_true", help="Create an admin user."
    )
    x0.add_argument("-U", "--create_user", action="store_true", help="Create a user.")
    x0.add_argument(
        "-D",
        "--dump",
        action="store",
        metavar="FILENAME",
        nargs="?",
        const=True,
        help="Dump all data into a tar.gz file.",
    )
    return p


def execute(pargs):
    "Execute the command."
    if pargs.debug:
        flask.current_app.config["DEBUG"] = True
        flask.current_app.config["LOGFORMAT"] = "%(levelname)-10s %(message)s"
    if pargs.create_admin:
        with blobserver.user.UserSaver() as saver:
            saver.set_username(input("username > "))
            saver.set_email(input("email > "))
            saver.set_password(getpass.getpass("password > "))
            saver.set_role(constants.ADMIN)
            saver.set_status(constants.ENABLED)
            saver["accesskey"] = None
    elif pargs.create_user:
        with blobserver.user.UserSaver() as saver:
            saver.set_username(input("username > "))
            saver.set_email(input("email > "))
            saver.set_password(getpass.getpass("password > "))
            saver.set_role(constants.USER)
            saver.set_status(constants.ENABLED)
            saver["accesskey"] = None
    elif pargs.dump:
        if pargs.dump == True:
            tarname = "dump_{}.tar.gz".format(time.strftime("%Y-%m-%d"))
        else:
            tarname = pargs.dump
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
        print(f"Wrote {count} files, {size} bytes to {tarname}")


def main():
    "Entry point for command line interface."
    parser = get_parser()
    pargs = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_usage()
    with blobserver.app.app.app_context():
        flask.g.db = utils.get_db()
        execute(pargs)


if __name__ == "__main__":
    main()
