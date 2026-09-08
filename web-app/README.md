# Seminars web app

This is a web-app to display upcoming talks and list potential speakers.
Data can be inserted through the app.

## Deployment
 - Make a github release
 - Run `sudo deploy-seminar-app <github-tag>` on swift
 - This updates the seminar-app service

 The app is ran on swift by the seminar-app user. The sqlite file is in this user's home

## Data
 - The sqlite database is backup up weekly with borg
 - Done by the seminar-app-backup service
 - `sudo -u seminar-app BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK=yes borg list /home/seminar-app/backup` to list the existing backups

## Gmail
The Gmail fetcher uses Google's OAuth desktop-app flow with the read-only Gmail
scope.

1. Create or select a Google Cloud project.
2. Enable the Gmail API for that project.
3. Configure the Google Auth platform consent screen.
4. Create an OAuth client with application type `Desktop app`.
5. Download the client secret JSON as `credentials.json` in this directory.
6. Run the fetcher once from this directory. A browser window will ask you to
   approve read-only Gmail access, then a local `token.json` will be saved for
   future runs.

The files `credentials.json` and `token.json` are ignored by git.
