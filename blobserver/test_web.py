"""Test the web site pages using Selenium.
https://selenium-python.readthedocs.io/index.html.
"""

import json
import os
import unittest

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

# Settings need to be define externally, by JSON file or environment variables.
try:
    with open("test_settings.json", "rb") as infile:
        settings = json.load(infile)
except IOError:
    settings = {}
for key in ["BASE_URL", "USER", "PASSWORD"]:
    try:
        settings[key] = os.environ[key]
    except KeyError:
        pass


class Homepage(unittest.TestCase):
    "Test the home page."

    def setUp(self):
        self.driver = selenium.webdriver.Chrome()

    def tearDown(self):
        self.driver.close()

    def test_home(self):
        "Test presence of table in home page and version indicator."
        self.driver.get(settings["BASE_URL"])
        self.assertIn("blobserver", self.driver.title)
        self.driver.find_element_by_id("blobs")
        with self.assertRaises(NoSuchElementException) as cm:
            self.driver.find_element_by_id("table")
        elem = self.driver.find_element_by_id("version")
        self.assertGreaterEqual(elem.text, "0.9.0")


class Search(unittest.TestCase):
    "Test the search page."

    def setUp(self):
        self.driver = selenium.webdriver.Chrome()

    def tearDown(self):
        self.driver.close()

    def test_home_page_search(self):
        "Do a simple search from the home page."
        self.driver.get(settings["BASE_URL"])
        elem = self.driver.find_element_by_name("term")
        elem.clear()
        elem.send_keys("covid")
        elem.send_keys(Keys.RETURN)
        self.assertIn("Search", self.driver.page_source)
        self.driver.find_element_by_id("blobs")
        with self.assertRaises(NoSuchElementException) as cm:
            self.driver.find_element_by_id("table")

    def test_search_page_search(self):
        "Do a simple search from the search page."
        self.driver.get(settings["BASE_URL"] + "/blobs/search")
        elem = self.driver.find_element_by_name("term")
        elem.clear()
        elem.send_keys("covid")
        elem.send_keys(Keys.RETURN)
        self.assertIn("Search", self.driver.page_source)
        self.driver.find_element_by_id("blobs")
        with self.assertRaises(NoSuchElementException) as cm:
            self.driver.find_element_by_id("table")



if __name__ == "__main__":
    unittest.main()
