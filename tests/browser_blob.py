"Test the web site pages for blob creation, update and delete."

import os
import os.path
import time
import unittest

import requests
import selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

import utils


class Blob(utils.BrowserTestCase):
    "Test creating, downloading, updating and deleting blob."

    def test_1_list_blobs(self):
        "Login and list the user's blobs."

        # Login page; fill in user name and password in form.
        self.driver.get(self.settings["BASE_URL"] + "user/login")
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(self.settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(self.settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form")
        elem.send_keys(Keys.RETURN)

        # Menu item "My blobs" is visible only when logged in.
        elem = self.driver.find_element_by_link_text("My blobs")
        elem.click()

        # Page listing the account's blobs.
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr")
        self.assertGreaterEqual(len(elems), 0)

    def test_2_create_blob(self):
        "Login and create a blob by upload."

        # Login page; fill in user name and password in form.
        self.driver.get(self.settings["BASE_URL"] + "user/login")
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(self.settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(self.settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form")
        elem.send_keys(Keys.RETURN)

        # Menu item "My blobs" is visible only when logged in.
        elem = self.driver.find_element_by_link_text("My blobs")
        elem.click()

        # Page listing the account's blobs.
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr")
        count = len(elems)

        # Go to upload page.
        elem = self.driver.find_element_by_link_text("Upload")
        elem.click()

        # Fill in form.
        elem = self.driver.find_element_by_name("description")
        elem.clear()
        description = "A test blob: this Python file."
        elem.send_keys(description)
        elem = self.driver.find_element_by_name("file")
        elem.clear()
        filename = os.path.basename(__file__)
        filepath = os.path.join(os.getcwd(), filename)
        elem.send_keys(os.path.join(filepath))
        elem = self.driver.find_element_by_xpath("//button[@type='submit']")
        elem.click()
        time.sleep(1)

        # Check the uploaded blob, compare to the file.
        elem = self.driver.find_element_by_xpath("//div[text()='Blob']/following-sibling::div/a")
        self.assertEqual(elem.text, filename)
        elem = self.driver.find_element_by_xpath("//div[text()='Description']/following-sibling::div/p")
        self.assertEqual(elem.text, description)

        # Find href for blob data, get and compare to source file.
        elem = self.driver.find_element_by_link_text(filename)
        response = requests.get(elem.get_attribute("href"))
        self.assertEqual(response.status_code, 200)
        with open(filepath, "rb") as infile:
            data = infile.read()
        self.assertEqual(data, response.content)

        # Delete the blob.
        elem = self.driver.find_element_by_xpath("//button[@type='submit' and contains(., 'Delete')]")
        elem.click()
        time.sleep(1)
        Alert(self.driver).accept()
        time.sleep(1)

        # Page listing the account's blobs.
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr")
        self.assertEqual(count, len(elems))

    def test_3_update_blob(self):
        "Login and create a blob by upload, and then update it."

        # Login page; fill in user name and password in form.
        self.driver.get(self.settings["BASE_URL"] + "user/login")
        self.assertIn("Login", self.driver.title)
        elem = self.driver.find_element_by_name("username")
        elem.clear()
        elem.send_keys(self.settings["USERNAME"])
        elem = self.driver.find_element_by_name("password")
        elem.clear()
        elem.send_keys(self.settings["PASSWORD"])
        elem = self.driver.find_element_by_id("login-form")
        elem.send_keys(Keys.RETURN)

        # Menu item "My blobs" is visible only when logged in.
        elem = self.driver.find_element_by_link_text("My blobs")
        elem.click()

        # Page listing the account's blobs.
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr")
        count = len(elems)

        # Go to upload page.
        elem = self.driver.find_element_by_link_text("Upload")
        elem.click()

        # Fill in form.
        elem = self.driver.find_element_by_name("description")
        elem.clear()
        description = "A test blob: this Python file."
        elem.send_keys(description)
        elem = self.driver.find_element_by_name("file")
        elem.clear()
        filename = os.path.basename(__file__)
        filepath = os.path.join(os.getcwd(), filename)
        elem.send_keys(filepath)
        elem = self.driver.find_element_by_xpath("//button[@type='submit']")
        elem.click()
        time.sleep(1)

        # Find href for blob data, get and compare to source file.
        elem = self.driver.find_element_by_link_text(filename)
        response = requests.get(elem.get_attribute("href"))
        self.assertEqual(response.status_code, 200)
        with open(filepath, "rb") as infile:
            data = infile.read()
        self.assertEqual(data, response.content)

        # Update the blob information via the form on the update page.
        elem = self.driver.find_element_by_link_text("Update")
        elem.click()
        elem = self.driver.find_element_by_name("description")
        elem.clear()
        description = "An updated test blob."
        elem.send_keys(description)
        elem = self.driver.find_element_by_xpath("//button[@type='submit']")
        elem.click()
        time.sleep(1)

        # Check the new description.
        elem = self.driver.find_element_by_xpath("//div[text()='Description']/following-sibling::div/p")
        self.assertEqual(elem.text, description)

        # Delete the blob.
        elem = self.driver.find_element_by_xpath("//button[@type='submit' and contains(., 'Delete')]")
        elem.click()
        time.sleep(1)
        Alert(self.driver).accept()
        time.sleep(1)

        # Page listing the account's blobs.
        elem = self.driver.find_element_by_id("blobs")
        elems = elem.find_elements_by_xpath("//tbody/tr")
        self.assertEqual(count, len(elems))


if __name__ == "__main__":
    unittest.main()
