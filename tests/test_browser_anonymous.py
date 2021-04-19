"Test the web site pages using Selenium. Not logged in."

import unittest

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

import utils

settings = utils.get_settings()


class Homepage(utils.BrowserTestCase):
    "Test the home page.."

    def test_home(self):
        "Test presence of table in home page and version indicator."
        self.driver.get(settings["BASE_URL"])
        self.assertIn("blobserver", self.driver.title)
        self.driver.find_element_by_id("blobs")
        with self.assertRaises(NoSuchElementException) as cm:
            self.driver.find_element_by_id("table")
        elem = self.driver.find_element_by_id("version")
        self.assertGreaterEqual(elem.text, "0.9.0")


class Search(utils.BrowserTestCase):
    "Test the search function."

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


class UsersBlobs(utils.BrowserTestCase):
    "Test the user's blobs page. Requires that some data is present."

    def test_users_blobs(self):
        "Fetch the list of users and the number of their blobs."
        self.driver.get(settings["BASE_URL"] + "/blobs/users")
        elems = self.driver.find_elements_by_class_name("blobserver-username")
        self.assertGreater(len(elems), 0)

    def test_user_blobs(self):
        "Fetch the list of blobs for the first user in the list."
        self.driver.get(settings["BASE_URL"] + f"/blobs/user/{settings['USERNAME']}")
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr/td")
        self.assertGreater(len(elems), 0)


class LoginUser(utils.BrowserTestCase):
    "Test login as a user."

    def test_login(self):
        "Go to login from the home page, and login."
        self.driver.get(settings["BASE_URL"])
        elem = self.driver.find_element_by_xpath("//form[@id='login-page']")
        elem = elem.find_element_by_tag_name("button")
        elem.click()
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form")
        elem.send_keys(Keys.RETURN)
        elem = self.driver.find_element_by_xpath("//a[text()='My blobs']")
        href = elem.get_attribute("href")
        self.assertEqual(href.split("/")[-1], settings["USERNAME"])
        elem.click()


if __name__ == "__main__":
    unittest.main()
