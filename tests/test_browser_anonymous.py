"Test the web site pages using Selenium. Not logged in."

import unittest

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

import utils

settings = utils.get_settings()


class Homepage(utils.BrowserTestCase):
    "Test the home page."

    def test_home(self):
        "Test presence of table in home page and version indicator."
        self.driver.get(settings["BASE_URL"])
        self.assertIn("blobserver", self.driver.title)
        # Table of blobs.
        self.driver.find_element_by_id("blobs")
        # Software versions displayed in footer in every page.
        elem = self.driver.find_element_by_id("version")
        self.assertGreaterEqual(elem.text, "0.9.0")


class Search(utils.BrowserTestCase):
    "Test the search function."

    def test_1_home_page_search(self):
        "Do a simple search from the home page."
        self.driver.get(settings["BASE_URL"])
        # Search form input field.
        elem = self.driver.find_element_by_name("term")
        elem.clear()
        elem.send_keys("covid")
        elem.send_keys(Keys.RETURN)
        # Search page.
        self.assertIn("Search", self.driver.page_source)
        # Search result table.
        self.driver.find_element_by_id("blobs")

    def test_2_search_page_search(self):
        "Do a simple search from the search page."
        # Search page.
        self.driver.get(settings["BASE_URL"] + "/blobs/search")
        # Search form input field.
        elem = self.driver.find_element_by_name("term")
        elem.clear()
        elem.send_keys("covid")
        elem.send_keys(Keys.RETURN)
        # Search page, but this time with results.
        self.assertIn("Search", self.driver.page_source)
        self.driver.find_element_by_id("blobs")


class UsersBlobs(utils.BrowserTestCase):
    "Test the user's blobs page. Requires that some data is present."

    def test_1_users_blobs(self):
        "Fetch the list of users and the number of their blobs."
        self.driver.get(settings["BASE_URL"] + "/blobs/users")
        elems = self.driver.find_elements_by_class_name("blobserver-username")
        self.assertGreater(len(elems), 0)

    def test_2_user_blobs(self):
        "Fetch the list of blobs for the first user in the list."
        self.driver.get(settings["BASE_URL"] + f"/blobs/user/{settings['USERNAME']}")
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr")
        self.assertGreater(len(elems), 0)


if __name__ == "__main__":
    unittest.main()
