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
