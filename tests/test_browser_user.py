"""Test browser user access and blob handling.

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
import playwright.sync_api
import requests

import utils


@pytest.fixture(scope="module")
def settings():
    "Get the settings from file 'settings.json' in this directory."
    return utils.get_settings(
        BASE_URL="http://localhost:5009", USERNAME=None, PASSWORD=None, ACCESSKEY=None
    )


def login_user(settings, page):
    "Log in."
    page.goto(settings["BASE_URL"])
    page.click("text=Login")
    assert page.url == f"{settings['BASE_URL']}/user/login?"
    page.click('input[name="username"]')
    page.fill('input[name="username"]', settings["USERNAME"])
    page.press('input[name="username"]', "Tab")
    page.fill('input[name="password"]', settings["PASSWORD"])
    page.click("id=login")
    assert page.url == f"{settings['BASE_URL']}/"


def test_user_page(settings, page):
    "Test access to the user's page."
    login_user(settings, page)

    title = f"User {settings['USERNAME']}"
    page.click(f"text={title}")
    assert title == page.locator("h2").inner_text()
    assert settings["ACCESSKEY"] == page.locator("#accesskey").inner_text()

    page.click("text=Logout")
    assert page.url.rstrip("/") == settings["BASE_URL"]


def test_user_blobs(settings, page):
    "List the user's blobs, create, get, update and delete one."
    login_user(settings, page)

    # Check number of blobs owned by the user.
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")
    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    locator = page.locator(".blobserver-blobinfo > a")
    count = locator.count()

    # Check that blob does not exist. No authentication required.
    filename = os.path.basename(__file__)
    url = f"{settings['BASE_URL']}/blob/{filename}"
    response = requests.get(url)
    assert response.status_code == http.client.NOT_FOUND

    # Create a new blob.
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")
    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    page.click("#upload")
    assert page.url == f"{settings['BASE_URL']}/blob/"
    page.click('textarea[name="description"]')
    description = "test upload"
    page.fill('textarea[name="description"]', description)
    with page.expect_file_chooser() as fc_info:
        page.click('input[name="file"]')
    file_chooser = fc_info.value
    file_chooser.set_files(filename)
    page.click('button:has-text("Upload")')
    assert page.url == f"{settings['BASE_URL']}/blob/{filename}/info"
    assert page.locator("#description").inner_text() == description

    # Check increase in number of blobs.
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")
    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    locator = page.locator(".blobserver-blobinfo > a")
    assert locator.count() == count + 1

    # Get and the blob content.
    url = f"{settings['BASE_URL']}/blob/{filename}"
    response = requests.get(url)
    assert response.status_code == http.client.OK
    with open(__file__, "rb") as infile:
        data = infile.read()
    assert response.content == data

    # # Modify the description.
    url = f"{settings['BASE_URL']}/blob/{filename}/info"
    page.goto(url)
    assert page.url == url
    page.click("#update")
    assert page.url == f"{settings['BASE_URL']}/blob/{filename}/update"
    page.click('textarea[name="description"]')
    description += " More text"
    page.fill('textarea[name="description"]', description)
    page.click('button:has-text("Update")')
    assert page.url == f"{settings['BASE_URL']}/blob/{filename}/info"
    assert page.locator("#description").inner_text() == description

    # Delete the blob.
    page.once("dialog", lambda dialog: dialog.accept())  # Callback for next click.
    page.click("#delete")
    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"

    # Check same number of blobs as before.
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")
    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    locator = page.locator(".blobserver-blobinfo > a")
    assert locator.count() == count
