"""Test API user access.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:5009/
"""

import http.client
import os.path
import urllib.parse

import pytest
import requests

import utils


@pytest.fixture(scope="module")
def settings():
    "Get the settings from file 'settings.json' in this directory."
    return utils.get_settings(BASE_URL="http://localhost:5009", USERNAME=None, ACCESSKEY=None)


def test_user_blobs_info(settings, page):
    "Test access to the user's blob info in JSON."
    url = f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}.json"
    headers = {"x-accesskey": settings["ACCESSKEY"]}
    response = requests.get(url, headers=headers)
    assert response.status_code == http.client.OK


def test_user_blob(settings, page):
    "Create, update and delete a blob."
    headers = {"x-accesskey": settings["ACCESSKEY"]}

    # Get number of blobs owned by the user.
    url = f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}.json"
    response = requests.get(url, headers=headers)
    assert response.status_code == http.client.OK
    data = response.json()
    count = len(data["blobs"])

    # Check that the new blob does not exist. No authentication required.
    filename = os.path.basename(__file__)
    url = f"{settings['BASE_URL']}/blob/{filename}"
    response = requests.get(url)
    assert response.status_code == http.client.NOT_FOUND

    # Create the new blob.
    with open(__file__, "rb") as infile:
        data = infile.read()
    response = requests.put(url, headers=headers, data=data)
    assert response.status_code == http.client.CREATED

    # Check increase in number of blobs.
    url = f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}.json"
    response = requests.get(url, headers=headers)
    assert response.status_code == http.client.OK
    assert len(response.json()["blobs"]) == count + 1

    # Check that blob exist. No authentication required.
    url = f"{settings['BASE_URL']}/blob/{filename}"
    response = requests.get(url)
    assert response.status_code == http.client.OK
    assert response.content == data

    # Modify the data, and update.
    data = data[:len(data)-10]
    response = requests.put(url, headers=headers, data=data)
    assert response.status_code == http.client.OK
    response = requests.get(url)
    assert response.status_code == http.client.OK
    assert response.content == data

    # Modify the description of the blob.
    url = f"{settings['BASE_URL']}/blob/{filename}/description"
    response = requests.get(url)
    assert response.status_code == http.client.OK
    assert response.content.decode() == ""
    description = "This is a new description.\nAnd a new line."
    response = requests.put(url, headers=headers, data=description)
    assert response.status_code == http.client.OK
    response = requests.get(url)
    assert response.status_code == http.client.OK
    assert response.content.decode() == description

    # Delete the blob.
    url = f"{settings['BASE_URL']}/blob/{filename}"
    response = requests.delete(url, headers=headers)
    assert response.status_code == http.client.NO_CONTENT

    # Check same number of blobs as before.
    url = f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}.json"
    response = requests.get(url, headers=headers)
    assert response.status_code == http.client.OK
    assert len(response.json()["blobs"]) == count
