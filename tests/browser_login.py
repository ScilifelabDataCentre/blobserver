"Test the web site pages using Selenium. Logging in."

import unittest

import selenium
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

import utils

settings = utils.get_settings()


class LoginUser(utils.BrowserTestCase):
    "Test login as a user."

    def test_1_login(self):
        "Starting from the home page, login to a user account."
        # Home page.
        self.driver.get(settings["BASE_URL"])
        elem = self.driver.find_element_by_xpath("//form[@id='login-formlink']")
        elem = elem.find_element_by_tag_name("button")
        elem.click()
        # Login page; fill in user name and password in form.
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form")
        elem.send_keys(Keys.RETURN)
        # Home page again.
        # Menu item "My blobs" is visible only when logged in.
        elem = self.driver.find_element_by_xpath("//a[text()='My blobs']")
        # Href in "My blobs" contains the user account name.
        href = elem.get_attribute("href")
        self.assertEqual(href.split("/")[-1], settings["USERNAME"])
        elem.click()
        # Page listing the account's blobs.
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr")
        self.assertGreater(len(elems), 0)

    def test_2_edit(self):
        "Starting from login page, login and edit user account."
        # Login page; fill in user name and password in form.
        self.driver.get(settings["BASE_URL"] + "user/login")
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form")
        elem.send_keys(Keys.RETURN)
        # Home page. Find link to user account page.
        elem = self.driver.find_element_by_link_text(f"User {settings['USERNAME']}")
        elem.click()
        # User account page. Record the current access key.
        elem = self.driver.find_element_by_xpath("//th[text()='Access key']/following-sibling::td")
        accesskey = elem.text
        # User account page; go to edit page.
        elem = self.driver.find_element_by_link_text("Edit")
        elem.click()
        # Edit page; fill in form to change access key and save.
        elem = self.driver.find_element_by_name("accesskey")
        elem.click()
        elem = self.driver.find_element_by_xpath("//button[@type='submit']")
        elem.click()
        # User account page. Check that the current access key is different.
        elem = self.driver.find_element_by_xpath("//th[text()='Access key']/following-sibling::td")
        self.assertNotEqual(elem.text, accesskey)

    def test_3_logout(self):
        "Starting from the home page, login to a user account, and logout."
        # Home page.
        self.driver.get(settings["BASE_URL"])
        elem = self.driver.find_element_by_xpath("//form[@id='login-formlink']")
        elem = elem.find_element_by_tag_name("button")
        elem.click()
        # Login page; fill in user name and password in form.
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form")
        elem.send_keys(Keys.RETURN)
        # Home page again. Find link to user account page.
        elem = self.driver.find_element_by_link_text(f"User {settings['USERNAME']}")
        elem.click()
        # User account page.
        elem = self.driver.find_element_by_xpath("//button[text()='Logout']")
        elem.click()
        # Home page again. The link "My blobs" is not present.
        with self.assertRaises(NoSuchElementException) as cm:
            self.driver.find_element_by_xpath("//a[text()='My blobs']")


if __name__ == "__main__":
    unittest.main()
