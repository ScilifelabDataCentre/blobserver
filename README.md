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

8. Edit the settings file. These settings can be configured using
   environment variables, if this is more convenient.
   - Set SECRET_KEY to a string of characters known only to you.
     It is required.
   - Set STORAGE_DIRPATH to the name of the directory where the
     blob files are to be stored. See point 7 above. It is required.
   - Set SERVER_NAME to the externally visible name of the server.
     This is used to form the URLs of the service. It is required.
   - Optionally set SITE_NAME to the name chosen for this service.
   - Optionally set SITE_ICON and SITE_LOGO to the names of files which,
     if they are defined, must be located in the
     `/path/to/blobserver/site/static` directory. See point 4 above.
   - Optionally set HOST_NAME and HOST_URL to fit your site.
     The name of the logo file is set by HOST_LOGO and, if it is
     defined, must be located in the `/path/to/blobserver/site/static`
     directory. See point 4 above.
   - Set CONTACT_EMAIL to an email address that handles queries about
     the service.

9. The first admin user cannot be created via the web interface. One must
   use one of the following two methods:

   1. Set the variables ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD,
      either in the settings file, or as environment variables. If the
      user account specified by that username has not been created already,
      it will be created before the first request to the app is processed.
   2. Use the command-line script `cli.py`. The option `-A` is used to
      create an admin user account. Use the `-h` option to get help.

10. Configure the reverse proxy (Apache, Nginx, or whatever) to serve
    the blobserver Flask app via uWSGI. It is a very bad idea to use
    the built-in Flask web server in production. It is **strongly**
    suggested to expose the blobserver using **https**, i.e. encrypted.

11. Once the web server is running, the first admin user account
    can be used to create new user accounts (ordinary users, or admins).
    Alternatively, the command-line script `cli.py` can be used
    to do this.
