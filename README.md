# blobserver

Simple web app to server blobs (files containing any data) publicly. A
file can be uploaded or updated by an authorized account, either via
the web interface or via a script.

Uses: Python3, Flask, Bootstrap 4, jQuery, DataTables, clipboard.js

## Installation

1. Download the blobserver software and install in a directory
   which is denoted symbolically here `/path/to/blobserver`

2. Set up your Python environment (Python 3.6 or later). Add
   the path `/path/to/blobserver` to the Python search path.

3. Install the third-party modules (see `requirements.txt`).

4. Create a directory `/path/to/blobserver/site`. This will contain
   files specific to your installation.

5. Copy the example settings file to your site directory.
   ```
   $ cd /path/to/blobserver
   $ cp blobserver/example_settings.json site/settings.json
   ```

6. If you wish to use a logo image file for your site, create
   a directory `/path/to/blobserver/site/static` and put it there.

7. The Sqlite3 database file and all the blob files must be stored
   in a directory to which the web server can create, read and write files.
   The name of this directory must be specified as STORAGE_DIRPATH in
   the settings file.

8. Edit the settings file.
   - Set SECRET_KEY to a string of characters known only to you.
   - Set STORAGE_DIRPATH to the name of the directory where the
     blob files are to be stored. See point 7 above.
   - Set SITE_ICON, SITE_LOGO and SITE_NAME to fit your site.
     The icon and logo files must be located in the
     `/path/to/blobserver/site/static` directory. See point 4 above.
   - Set HOST_NAME, HOST_URL and HOST_LOGO to fit your site.
     The logo file must be located in the
     `/path/to/blobserver/site/static` directory. See point 4 above.
   - Set CONTACT_EMAIL to an email address for your site administrator.

9. Configure the reverse proxy (Apache, Nginx, or whatever) to serve
   the blobserver Flask app via uWSGI. It is a very bad idea to use
   the built-in Flask web server in production. It is **strongly**
   suggested to expose the blobserver using **https**, i.e. encrypted.

10. You need to create the first admin user account in the system.
    Once this admin account exists, it can be used to register other
    accounts via the web interface.  The first admin account can be
    created only with the command-line script `cli.py`. Use the `-h`
    option to get help.
