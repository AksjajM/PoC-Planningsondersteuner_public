# PoC Planning Support Tool

This repository contains the Django Proof of Concept (PoC) for the TOPdesk Support NL/BE Planning Support Tool.

The goal of this PoC is to centralize planning-related information such as employee availability, roles, leave and capacity rules into a single web application that serves as a **Single Source of Truth**.

---

## Technology stack

- Python
- Django
- SQLite (PoC database)
- Docker
- GitLab CI/CD
- Pylint

---

## Project structure

```text
.
├── config/              # Django project configuration
├── planning/            # Planning application
│   ├── management/      # Django management commands
│   ├── migrations/      # Database migrations
│   └── tests/           # Automated tests
├── templates/           # Shared templates
├── static/              # Static files
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── .env.example
├── .gitignore
├── .pylintrc
└── .gitlab-ci.yml
```

The project intentionally remains a lightweight Django Proof of Concept. The `config` package contains the project configuration, while the `planning` application contains all planning-related functionality.

---

## Quick start

To run the application locally:

1. Create a virtual environment.
2. Install the project dependencies.
3. Copy `.env.example` to `.env`.
4. Run the database migrations.
5. Seed the demo data.
6. Start the Django development server.
7. Log in using one of the demo accounts.

The sections below describe each step in more detail.

---

## Run the application with Docker

Build the Docker image:

```bash
docker build -t poc-planningsondersteuner .
```

Start the container:

```bash
MSYS_NO_PATHCONV=1 docker run --rm -p 8000:8000 \
  -e DEBUG=True \
  -e SECRET_KEY=dev-only-change-me \
  -e ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000 \
  poc-planningsondersteuner
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Run the application locally

### 1. Create a virtual environment

```bash
py -m venv .venv
source .venv/Scripts/activate
```

### 2. Install the dependencies

Install the application:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Optional development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

### 3. Configure the application

Create a local configuration file:

```bash
cp .env.example .env
```

For local development ensure that:

```text
DEBUG=True
```

is configured.

### 4. Apply the database migrations

```bash
python manage.py migrate
```

### 5. Seed the demo data

Create a reproducible local environment containing demo users, demo roles and user-role assignments:

```bash
python manage.py seed_demo_data
```

Create a demo administrator as well:

```bash
python manage.py seed_demo_data --with-admin
```

By default all demo users receive the password:

```text
ChangeMe123!
```

Use a custom password:

```bash
python manage.py seed_demo_data --password MyPassword123!
```

or

```bash
DEMO_USER_PASSWORD=MyPassword123! python manage.py seed_demo_data
```

### 6. Start the application

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Log in using one of the demo accounts listed below.

---

## Demo accounts

After running the seed command the following accounts are available.

| Username | Password | Purpose |
|----------|----------|---------|
| planner1 | ChangeMe123! | Demo planner |
| employee1 | ChangeMe123! | Demo employee |
| employee2 | ChangeMe123! | Demo employee |

If you used:

```bash
python manage.py seed_demo_data --with-admin
```

an additional administrator account is created.

| Username | Password |
|----------|----------|
| admin | ChangeMe123! |

> **Note**
>
> The demo accounts are intended for local development only.
>
> Running the seed command multiple times is safe. Existing users, roles and assignments are reused, while the passwords are updated.

---

## Login

Application login:

```text
http://127.0.0.1:8000/login/
```

Django administration:

```text
http://127.0.0.1:8000/admin/
```

The administrator account is only available when the demo data is created using the `--with-admin` option.

---

## Reset the local database

If you want to recreate the complete local environment:

Git Bash:

```bash
rm db.sqlite3
```

Windows PowerShell:

```powershell
Remove-Item db.sqlite3
```

Then run:

```bash
python manage.py migrate
python manage.py seed_demo_data --with-admin
```

This recreates the SQLite database together with all demo users, demo roles and user-role assignments.

---

## Configuration

The application uses the following environment variables:

```text
DEBUG
SECRET_KEY
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
DATABASE_PATH
DEMO_USER_PASSWORD
```

Create a local configuration:

```bash
cp .env.example .env
```

Do not commit a real `.env` file.

Production secrets should always be configured through GitLab CI/CD variables or the deployment environment.

---

## Validation commands

Run the Django system check:

```bash
python manage.py check
```

Check for missing migrations:

```bash
python manage.py makemigrations --check --dry-run
```

Apply database migrations:

```bash
python manage.py migrate
```

Run all automated tests:

```bash
python manage.py test
```

Regenerate the demo data:

```bash
python manage.py seed_demo_data
```

Generate a JUnit test report:

```bash
python -m pytest --ds=config.settings --junitxml=report.xml
```

The generated `report.xml` file should not be committed.

---

## Code quality

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run Pylint:

```bash
python -m pylint --rcfile=.pylintrc config planning
```

Generate a GitLab Code Quality report:

```bash
python -m pylint --exit-zero \
  --rcfile=.pylintrc \
  --output-format=pylint_gitlab.GitlabCodeClimateReporter \
  config planning > gl-code-quality-report.json
```

The current quality profile enables only **Error** and **Fatal** checks (`E,F`).

An empty report:

```json
[]
```

means that no findings were detected.

---

## CI/CD

The GitLab pipeline performs:

- Django system checks
- Migration checks
- Automated tests
- JUnit test report generation
- Pylint static analysis
- GitLab Code Quality report generation
- SAST
- Secret Detection
- Docker packaging
- Deployment to the configured VM-Docker environment

The same Pylint configuration is used locally and in GitLab through `.pylintrc`.

---

## Project status

This repository contains the Proof of Concept for the TOPdesk Planning Support Tool.

The application is currently under active development as part of an HBO-ICT Software Engineering graduation project. Functionality is implemented incrementally through Jira stories, validated using automated tests and reviewed through GitLab Merge Requests..