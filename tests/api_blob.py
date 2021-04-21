"Test the API interface for blob creation."

import os
import os.path
import unittest

import requests

import utils


class Blob(unittest.TestCase):
    "Test the API interface for blob creation."

    def setUp(self):
        self.settings = utils.get_settings()

    def test_1_create_blob(self):
        "Create a blob by HTTP PUT."
        headers = {"x-accesskey": self.settings["ACCESSKEY"]}

        # Get the file data; this Python file.
        filename = os.path.basename(__file__)
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, "rb") as infile:
            data = infile.read()

        # Create the blob.
        url = self.settings["BASE_URL"] + f"blob/{filename}"
        response = requests.put(url, headers=headers, data=data)
        self.assertEqual(response.status_code, 201)

        # Check the data in it.
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data, response.content)

        # Delete the blob.
        response = requests.delete(url, headers=headers)
        self.assertEqual(response.status_code, 204)

    def test_2_update_blob(self):
        "Create and update a blob by HTTP PUT."
        headers = {"x-accesskey": self.settings["ACCESSKEY"]}

        # Get the file data; this Python file.
        filename = os.path.basename(__file__)
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, "rb") as infile:
            data = infile.read()

        # Create the blob.
        url = self.settings["BASE_URL"] + f"blob/{filename}"
        response = requests.put(url, headers=headers, data=data)
        self.assertEqual(response.status_code, 201)

        # Update the blob.
        data = b"Some fake data."
        response = requests.put(url, headers=headers, data=data)
        self.assertEqual(response.status_code, 200)
        
        # Check the data in it.
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data, response.content)

        # Delete the blob.
        response = requests.delete(url, headers=headers)
        self.assertEqual(response.status_code, 204)


if __name__ == "__main__":
    unittest.main()
