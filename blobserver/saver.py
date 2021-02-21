"Base entity saver context class."

import copy
import json
import os.path
import sys

import flask

from blobserver import constants
from blobserver import utils


class BaseSaver:
    "Base entity saver context."

    LOG_EXCLUDE_PATHS = [["modified"]]  # Exclude from log info.
    LOG_HIDE_VALUE_PATHS = []           # Do not show value in log.

    def __init__(self, doc=None):
        if doc is None:
            self.original = {}
            self.doc = {}
            self.initialize()
        else:
            self.original = copy.deepcopy(doc)
            self.doc = doc
        self.prepare()

    def __enter__(self):
        return self

    def __exit__(self, etyp, einst, etb):
        if etyp is not None: return False
        self.finalize()
        self.doc["modified"] = utils.get_time()
        self.upsert()
        self.add_log()

    def __getitem__(self, key):
        return self.doc[key]

    def __setitem__(self, key, value):
        self.doc[key] = value

    def initialize(self):
        "Initialize the new entity."
        self.doc["iuid"] = utils.get_iuid()
        self.doc["created"] = utils.get_time()

    def prepare(self):
        "Preparations before making any changes."
        pass

    def finalize(self):
        "Final operations and checks on the entity."
        pass

    def upsert(self):
        "Actually insert or update the entity in the database."
        raise NotImplementedError

    def add_log(self):
        """Add a log entry recording the the difference betweens the current
        and the original entity.
        """
        entry = {"docid": self.doc["iuid"],
                 "diff": json.dumps(self.diff(self.original, self.doc)),
                 "timestamp": utils.get_time()}
        if hasattr(flask.g, "current_user") and flask.g.current_user:
            entry["username"] = flask.g.current_user["username"]
        if flask.has_request_context():
            entry["remote_addr"] = str(flask.request.remote_addr)
            entry["user_agent"] = str(flask.request.user_agent)
        else:
            entry["user_agent"] = os.path.basename(sys.argv[0])
        with flask.g.db:
            fields = ",".join([f"'{k}'" for k in entry.keys()])
            args = ",".join(["?"] * len(entry))
            flask.g.db.execute(f"INSERT INTO logs ({fields}) VALUES ({args})",
                               list(entry.values()))

    def diff(self, old, new, stack=None):
        """Find the differences between the old and the new documents.
        Uses a fairly simple algorithm which is OK for shallow hierarchies.
        """
        if stack is None: stack = []
        added = {}
        removed = {}
        updated = {}
        new_keys = set(new.keys())
        old_keys = set(old.keys())
        for key in new_keys.difference(old_keys):
            stack.append(key)
            if stack not in self.LOG_EXCLUDE_PATHS:
                if stack in self.LOG_HIDE_VALUE_PATHS:
                    added[key] = "<hidden>"
                else:
                    added[key] = new[key]
            stack.pop()
        for key in old_keys.difference(new_keys):
            stack.append(key)
            if stack not in self.LOG_EXCLUDE_PATHS:
                if stack in self.LOG_HIDE_VALUE_PATHS:
                    removed[key] = "<hidden>"
                else:
                    removed[key] = old[key]
            stack.pop()
        for key in new_keys.intersection(old_keys):
            stack.append(key)
            if stack not in self.LOG_EXCLUDE_PATHS:
                new_value = new[key]
                old_value = old[key]
                if isinstance(new_value, dict) and isinstance(old_value, dict):
                    changes = self.diff(old_value, new_value, stack)
                    if changes:
                        if stack in self.LOG_HIDE_VALUE_PATHS:
                            updated[key] = "<hidden>"
                        else:
                            updated[key] = changes
                elif new_value != old_value:
                    if stack in self.LOG_HIDE_VALUE_PATHS:
                        updated[key]= dict(new_value="<hidden>",
                                           old_value="<hidden>")
                    else:
                        updated[key]= dict(new_value= new_value,
                                           old_value=old_value)
            stack.pop()
        result = {}
        if added:
            result['added'] = added
        if removed:
            result['removed'] = removed
        if updated:
            result['updated'] = updated
        return result
