"Test runner."

import unittest

import browser_anonymous
import browser_login
import browser_blob
import api_blob

loader = unittest.TestLoader()
suite = unittest.TestSuite()

suite.addTests(loader.loadTestsFromModule(browser_anonymous))
suite.addTests(loader.loadTestsFromModule(browser_login))
suite.addTests(loader.loadTestsFromModule(browser_blob))
suite.addTests(loader.loadTestsFromModule(api_blob))

runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite)
