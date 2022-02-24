"""Test browser anonymous access.

After installing from PyPi using the 'requirements.txt' file, one must do:
$ playwright install

To run while displaying browser window:
$ pytest --headed

Much of the code below was created using the playwright code generation feature:
$ playwright codegen http://localhost:5009/
"""

import http.client
import urllib.parse

import pytest
import playwright.sync_api
import requests

import utils


@pytest.fixture(scope="module")
def settings():
    "Get the settings from file 'settings.json' in this directory."
    return utils.get_settings(BASE_URL="http://localhost:5009")


def test_status(settings, page):
    response = requests.get(f"{settings['BASE_URL']}/status")
    assert response.status_code == http.client.OK
    data = response.json()
    assert data["status"] == "ok"


def test_about(settings, page):  # 'page' fixture from 'pytest-playwright'
    "Test access to 'About' pages."
    page.set_default_navigation_timeout(3000)

    page.goto(settings["BASE_URL"])
    page.click("text=About")
    page.click("text=Contact")
    assert page.url == f"{settings['BASE_URL']}/about/contact"

    page.goto(settings["BASE_URL"])
    page.click("text=About")
    page.click("text=Software")
    assert page.url == f"{settings['BASE_URL']}/about/software"


def test_blobs(settings, page):
    "Test access to blobs' list pages."
    page.goto(settings["BASE_URL"])
    page.click("text=Users' blobs")
    assert page.url == f"{settings['BASE_URL']}/blobs/users"

    page.goto(settings["BASE_URL"])
    page.click("text=All blobs")
    assert page.url == f"{settings['BASE_URL']}/blobs/all"

    # Get the actual blobs.
    locator = page.locator(".blobserver-bloblink > a")
    hrefs = []
    for i in range(locator.count()):
        href = urllib.parse.unquote(locator.nth(i).get_attribute("href"))
        hrefs.append(f"{settings['BASE_URL']}{href}")
    for href in hrefs:
        response = requests.get(href)
        assert response.status_code == http.client.OK

    # Get information pages about each blob.
    locator = page.locator(".blobserver-blobinfo > a")
    hrefs = []
    for i in range(locator.count()):
        href = urllib.parse.unquote(locator.nth(i).get_attribute("href"))
        hrefs.append(f"{settings['BASE_URL']}{href}")
    for href in hrefs:
        page.goto(href)


def test_search(settings, page):
    "Test the search function."
    page.goto(settings["BASE_URL"])
    page.fill('input[type="search"]', "test")
    page.press('input[type="search"]', "Enter")
    assert page.url == f"{settings['BASE_URL']}/blobs/search?term=test"

    # page.wait_for_timeout(3000)
