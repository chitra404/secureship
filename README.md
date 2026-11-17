# SecureShip

SecureShip is a small shipment tracking app and a DevSecOps project.

You can create a shipment, get a tracking code, and check its progress. The app uses FastAPI for the API, a simple web page for the frontend, and PostgreSQL to save shipment data.

The main focus of this project is the security pipeline that checks the Docker image before it is released.

## What the project does

The shipment app lets you:

- Create a shipment.
- Get a tracking code.
- View shipment details and status history.
- Move a shipment through its status steps.

The status steps are:

`Created → In transit → Out for delivery → Delivered`

The GitHub Actions pipeline checks the application and Docker image before publishing it.

## Security pipeline

The pipeline has two jobs.

### 1. Build and scan

This job runs for pull requests and pushes. It:

1. Runs the tests with pytest.
2. Builds the Docker image.
3. Scans the image with Trivy.
4. Stops the pipeline if it finds a fixable CRITICAL vulnerability.
5. Creates an SPDX SBOM with Syft.

This job does not publish or sign the image.

### 2. Publish and sign

This job runs only after a successful push to `main`, and only when the first job passes. It:

1. Publishes the image to GitHub Container Registry (GHCR).
2. Signs the image with Cosign using GitHub OIDC.
3. Verifies the image signature.

The pipeline passes the same image from the scan job to the publish job. This means the image that gets published is the image that was scanned.

## Tools used

| Tool | Use |
|---|---|
| Python and FastAPI | Backend API |
| HTML, CSS and JavaScript | Frontend |
| PostgreSQL | Stores shipment data |
| SQLAlchemy | Connects the application to PostgreSQL |
| Alembic | Manages database changes |
| pytest | Runs tests |
| Docker | Builds the application image |
| GitHub Actions | Runs the pipeline |
| Trivy | Scans the image for vulnerabilities |
| Syft | Creates the SBOM |
| Cosign | Signs and verifies the image |

## Project structure

```text
secureship/
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       └── secure-pipeline.yml
├── app/
│   ├── static/
│   │   ├── app.js
│   │   ├── index.html
│   │   └── style.css
│   ├── crud.py
│   ├── database.py
│   ├── dependencies.py
│   ├── main.py
│   ├── models.py
│   └── schemas.py
├── migrations/
│   └── versions/
├── scripts/
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── docs/
├── Dockerfile
├── Makefile
├── alembic.ini
├── requirements.txt
├── requirements-dev.txt
└── pytest.ini
```

## Requirements

You need:

- Git
- Python 3.12 or newer
- Docker
- PostgreSQL
- A GitHub account

Trivy, Syft and Cosign are optional if you only want to run the application locally. They are used by the security pipeline.

## Run it locally

### 1. Get the project

```bash
git clone https://github.com/chitra404/secureship.git
cd secureship
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the dependencies

```bash
pip install -r requirements-dev.txt
```

### 4. Set the database connection

Create a PostgreSQL database and user for local development. Then set the connection URL in your terminal:

```bash
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE"
```

Replace the example values with your local PostgreSQL details. Do not commit your real database URL or password to Git.

### 5. Create the database tables

Run the migrations:

```bash
alembic upgrade head
```

### 6. Start the application

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

Stop the server with `Ctrl+C`.

## Using the app

1. Enter the sender, receiver, destination and item.
2. Create the shipment.
3. Keep the tracking code that appears.
4. Use the tracking code to view the shipment.
5. Advance the status to see the next step.

Shipment information is stored in PostgreSQL, so it is not lost when the application restarts.

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Opens the web page |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/status` | Shows service status and shipment count |
| `GET` | `/api/v1/shipments` | Lists shipments |
| `POST` | `/api/v1/shipments` | Creates a shipment |
| `GET` | `/api/v1/shipments/{code}` | Gets one shipment by tracking code |
| `POST` | `/api/v1/shipments/{code}/advance` | Moves a shipment to the next status |
| `GET` | `/docs` | Opens the API documentation |

## Database migrations

The project uses Alembic to manage database changes.

After changing the database models, create a migration:

```bash
alembic revision --autogenerate -m "describe the change"
```

Review the generated migration before applying it.

Apply migrations with:

```bash
alembic upgrade head
```

Check the current migration:

```bash
alembic current
```

Check whether the models and database schema are in sync:

```bash
alembic check
```

## Run the tests

The tests use a separate PostgreSQL database. Do not point `TEST_DATABASE_URL` at your development or production database.

Set the test database URL:

```bash
export TEST_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:PORT/TEST_DATABASE"
```

Then run:

```bash
python -m pytest -v
```

The test setup creates the required tables and clears test data between tests. It also removes the test tables when the test session finishes. Use a separate test database that contains no data you need to keep.

## Run the security checks locally

If you have Trivy and Syft installed, you can run:

```bash
make scan
make sbom
```

You can also run the project checks with:

```bash
make check
```

Some checks are skipped when the related tools are not installed.

A vulnerability report needs to be reviewed. A finding does not always mean the application can be exploited, but it should not be ignored. Check the affected package and available fix before making a decision.

## GitHub Actions

After pushing to `main`, open the **Actions** tab in the GitHub repository to see the pipeline result.

When the pipeline passes, you should be able to find:

- The test, build and scan results.
- The Trivy report and SBOM artifacts.
- The published image in GHCR.
- The image digest and Cosign verification result.

Pull requests can run the build and scan job, but they cannot publish or sign an image.

## Security notes

- The publish job runs only after the build and scan job succeeds.
- Pull requests do not get permission to publish packages or request the signing identity.
- Cosign uses GitHub OIDC for keyless signing. The workflow does not need a long-lived private signing key.
- GitHub Actions are pinned to commit SHAs in the workflow. Dependabot is used to suggest updates.
- The Trivy gate blocks fixable CRITICAL findings. Passing the scan does not mean the image has no vulnerabilities.
- A valid image signature shows which workflow identity signed the image. It does not prove that the application itself is free from security issues.

SecureShip is a learning and demonstration project. Review the API access rules and deployment settings before using it with real shipment or customer data.

## Useful scripts

The helper scripts are in the `scripts/` directory.

| Script | Purpose |
|---|---|
| `./scripts/setup.sh` | Sets up the Python environment and installs dependencies |
| `./scripts/check.sh` | Runs the available project checks |
| `./scripts/verify-image.sh OWNER/REPO sha256:DIGEST` | Verifies a published image |
| `./scripts/demo-gate.sh start` | Starts the release-gate demonstration |
| `./scripts/demo-gate.sh cleanup` | Cleans up the demonstration branch |

You can also use:

```bash
make setup
make check
```

## Links

- GitHub repository: https://github.com/chitra404/secureship
- Live application: https://secureship-1sce.onrender.com

