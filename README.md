# CESOMS Final Submission Folder

This folder is the submission-formatted version of the Campus Event and Student Organization Management System.

## Structure

```txt
CESOMS_f/
├── README.md
├── docs/
├── db/
├── backend/
├── frontend/
├── reports/
├── roles/
```

## What Lives Where

- `backend/`: Flask backend, authentication, business logic, database access
- `frontend/`: templates and static assets for the GUI
- `db/`: database config example and database-related files
- `docs/`: diagrams, screenshots, and final report support files
- `reports/`: generated report artifacts
- `roles/`: team member contribution notes

## Running The App

1. Open a terminal in `CESOMS_f/backend/`
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Add database config in `CESOMS_f/db/DB_info.txt`

Example:

```txt
host=YOUR_DB_HOST
user=YOUR_DB_USER
password=YOUR_DB_PASSWORD
database=YOUR_DB_NAME
port=3306
```

4. Start the app:

```powershell
python app.py
```

5. Open:

```txt
http://127.0.0.1:5000
```

## Authentication Notes

- Student signup is available from the login page
- The first admin can be initialized from the browser if no admin login exists yet
- You can also bootstrap an admin from `backend/bootstrap_admin.py`

Example:

```powershell
python bootstrap_admin.py --admin-id ADM-1 --first-name Alex --last-name Rivera --email admin@school.edu --department "Student Affairs" --password "ChangeMe123!"
```

## Security Notes

- Passwords are hashed with Werkzeug
- Authentication records are stored in the database
- Parameterized SQL queries are used throughout the app for basic SQL injection protection
