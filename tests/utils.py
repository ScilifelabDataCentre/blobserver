"Utilities for tests."

import http.client
import json
import os

BLOBSERVER_VERSION = "1.1.1"


def get_settings(**defaults):
    "Update the default settings by the contents of the 'settings.json' file."
    result = defaults.copy()
    settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
    with open(settings_path, "rb") as infile:
        data = json.load(infile)
    for key in result:
        try:
            result[key] = data[key]
        except KeyError:
            pass
        if result.get(key) is None:
            raise KeyError(f"Missing {key} value in settings.")
    # Remove any trailing slash in the base URL.
    result["BASE_URL"] = result["BASE_URL"].rstrip("/")
    return result


class Writer:
    def __init__(self):
        self.outfile = open("out.txt", "w")

    def __call__(self, data):
        self.outfile.write(json.dumps(data))

    def __delete__(self):
        self.outfile.close()
