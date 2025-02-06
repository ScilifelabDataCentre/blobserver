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
    # href_value = page.locator('a.btn.btn-outline-secondary').get_attribute('href')
    # print(f"The href value is: {href_value}")
    # Check number of blobs owned by the user.

    print("Before clicking 'My blobs'")
    print(f"Current URL: {page.url}")
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")

    print("After clicking 'My blobs'")
    print(f"Current URL2: {page.url}")
    expected_url = f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    print(f"Expected URL: {expected_url}")
    print(f"Actual URL: {page.url}")

    # Use rstrip('/') to handle trailing slashes
    assert page.url.rstrip('/') == expected_url.rstrip('/'), f"URL mismatch: {page.url} != {expected_url}"

    locator = page.locator(".blobserver-blobinfo > a")
    count = locator.count()

    # Check that blob does not exist. No authentication required.
    filename = os.path.basename(__file__)
    print(f"filename1: {filename}")
    url = f"{settings['BASE_URL']}/blob/{filename}"
    response = requests.get(url)
    assert response.status_code == http.client.NOT_FOUND

    # Create a new blob.
    # page.click("text=My blobs")
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")

    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    page.click("#upload")
    assert page.url == f"{settings['BASE_URL']}/blob/"
    page.click('textarea[name="description"]')
    description = "test upload"
    page.fill('textarea[name="description"]', description)

     # Find a .txt file in the current working directory
    txt_files = [f for f in os.listdir(os.getcwd()) if f.endswith('.txt')]
    if not txt_files:
        raise FileNotFoundError("No .txt file found in the current working directory.")
    
    filename = txt_files[0]  # Choose the first .txt file found
    print(f"Selected file for upload: {filename}")

    with page.expect_file_chooser() as fc_info:
        page.click('input[name="file"]')

    file_chooser = fc_info.value
    file_chooser.set_files(filename)
    print("After setting files")
    
    # print(f"filename: {filename}")
    # file_chooser = fc_info.value
    # file_chooser.set_files(filename)
    # print("After setting files")

    page.click('button:has-text("Upload")')
    assert page.url == f"{settings['BASE_URL']}/blob/{filename}/info"
    assert page.locator("#description").inner_text() == description

    # Check increase in number of blobs.
    # page.click("text=My blobs")
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")
    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    locator = page.locator(".blobserver-blobinfo > a")
    assert locator.count() == count + 1

    # Get and the blob content.
    url = f"{settings['BASE_URL']}/blob/{filename}"
    response = requests.get(url)
    assert response.status_code == http.client.OK
    with open(filename, "rb") as infile:
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
    # page.click("text=My blobs")
    page.click("#top_navbar >> a.nav-link:has-text('My blobs')")
    assert page.url == f"{settings['BASE_URL']}/blobs/user/{settings['USERNAME']}"
    locator = page.locator(".blobserver-blobinfo > a")
    assert locator.count() == count
