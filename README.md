# SecureShip: DevSecOps Supply Chain Security Pipeline

SecureShip is a practical reference project that shows how to **test, build, scan,
approve, publish, sign and verify** a Docker container image using an automated
GitHub Actions pipeline.

The sample workload is a small **shipment tracker**: a simple web page (frontend) backed by
a Python FastAPI REST API (backend). You can create shipments, get a tracking code, search
them, and move each one through `Created → In transit → Out for delivery → Delivered`.
The app is the thing being protected; the real project is the **pipeline around it**.

No AWS account, credit card, Kubernetes cluster or paid service is needed.

## What the pipeline does

| # | Step | Tool | Runs on |
|---|------|------|---------|
| 1 | Run tests | pytest | PR + push |
| 2 | Build the Docker image | Docker | PR + push |
| 3 | Scan the image, write a HIGH/CRITICAL report | Trivy | PR + push |
| 4 | **Release gate**: fail on any fixable CRITICAL finding | Trivy | PR + push |
| 5 | Generate an SPDX SBOM | Syft | PR + push |
| 6 | Publish the approved image to GHCR | Docker | push to `main` only |
| 7 | Sign the image digest (keyless) | Cosign | push to `main` only |
| 8 | Verify the signature against a fixed identity | Cosign | push to `main` only |

The pipeline is split into **two jobs**:

- `build-scan` (steps 1-5) is **read-only**. It runs for pull requests and cannot publish or sign.
- `publish-sign` (steps 6-8) runs **only** for a push to `main`, and **only** if `build-scan` passed.
  It is the only job allowed to write packages or request a signing identity (OIDC) token.

The exact image that passed the scan is handed to the publish job, so what you scan
is what you ship.

## Project layout

```text
secureship/
├── .github/
│   ├── dependabot.yml              # keeps pins and dependencies fresh
│   └── workflows/secure-pipeline.yml
├── app/
│   ├── main.py                     # FastAPI routes + security headers
│   ├── schemas.py                  # request/response models and validation
│   ├── store.py                    # in-memory shipment storage
│   └── static/                     # frontend: index.html, style.css, app.js
├── scripts/                        # helper Bash scripts (see below)
├── tests/                          # pytest tests
├── docs/                           # architecture, step-by-step guide, policy
├── Dockerfile
├── Makefile
├── pytest.ini
├── requirements.txt                # runtime dependencies (pinned)
└── requirements-dev.txt            # test dependencies (pinned)
```

## Requirements

- Git
- Python 3.12 or newer, with `pip`
- Docker Engine or Docker Desktop
- A GitHub account
- Optional, for running the security tools on your own machine: Trivy, Syft, Cosign

## 1. Run it locally

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/** in your browser. That is the web app.

Stop the server with `Ctrl+C`.

### Using the app

1. Fill in *Sender*, *Receiver*, *Destination* and *Item*, then click **Create shipment**.
2. A tracking code like `SS-1A2B3C4D` appears and the shipment shows in the list.
3. Click **Advance status** to move it to the next stage, until it says *Delivered*.
4. Use the search box to find a shipment by tracking code or receiver name.

Data is kept in memory only, so it resets when the app restarts. That is deliberate:
there is no database to secure, and the container can run with a read-only filesystem.

### API endpoints

| Method | Path | What it does |
|--------|------|--------------|
| GET | `/` | The web page |
| GET | `/health` | Health check (used by Docker) |
| GET | `/api/v1/status` | Service status, version, shipment count |
| GET | `/api/v1/shipments` | List shipments (newest first) |
| POST | `/api/v1/shipments` | Create a shipment |
| GET | `/api/v1/shipments/{code}` | Track one shipment |
| POST | `/api/v1/shipments/{code}/advance` | Move to the next status |
| GET | `/docs` | Interactive API docs |

The input is validated (length limits, no unknown fields), the number of stored
shipments is capped, and the page ships with a strict Content-Security-Policy.

## 2. Run it in Docker

```bash
make build          # or: docker build -t secureship-api:local .
make docker-run     # runs with a read-only filesystem and all capabilities dropped
```

Then open http://127.0.0.1:8000/ (the app) or http://127.0.0.1:8000/health. To confirm the container is not root:

```bash
docker run --rm --entrypoint id secureship-api:local     # expect uid=10001(appuser)
```

## 3. Run the security tools locally (optional)

Install Trivy and Syft from their official documentation, then:

```bash
make scan           # Trivy: fails on fixable CRITICAL findings
make sbom           # Syft: writes sbom.spdx.json
```

A scanner finding is not proof that something is exploitable. Investigate it,
upgrade the package or base image, and document any justified exception
(see `docs/SECURITY_POLICY.md`). Never just switch the scan off.

## Helper scripts (Bash)

All scripts are in `scripts/`. Run them from the project root. On Windows use Git Bash or WSL.

| Script | What it does |
|--------|--------------|
| `./scripts/setup.sh` | Checks Python 3.12+, creates `.venv`, installs dependencies, runs the tests |
| `./scripts/check.sh` | Pre-push check: tests, plus Docker build, non-root test, hardened container health test, Trivy gate and SBOM **if those tools are installed** (otherwise they are skipped). Exits with an error if anything fails |
| `./scripts/push-to-github.sh USERNAME [REPO]` | First-time push to a new empty GitHub repo (validates the lowercase name, sets `main`, commits, pushes) |
| `./scripts/verify-image.sh OWNER/REPO sha256:DIGEST` | Verifies a published image with Cosign against the fixed workflow identity |
| `./scripts/demo-gate.sh start` / `cleanup` | Creates (and later removes) a throwaway branch with a vulnerable dependency to prove the release gate blocks it |

Shortcuts: `make setup` and `make check`.

## 4. Put it on GitHub

Easiest way: create the empty repository on GitHub, then run
`./scripts/push-to-github.sh YOUR-USERNAME`. Or do it by hand:

1. On GitHub, create a new **empty** repository named `secureship`
   (lowercase; GHCR image names must be lowercase).
2. Extract the ZIP and open a terminal **inside** the `secureship` folder.
3. Run:

```bash
git init
git add .
git commit -m "Initial SecureShip implementation"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/secureship.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username.

The push to `main` starts the pipeline. **You do not need a personal access token
or any repository secret.** The workflow uses the built-in `GITHUB_TOKEN`, and the
two permissions it needs (`packages: write` and `id-token: write`) are declared
in the workflow file itself, only on the publish job.

## 5. Check that it worked

1. Open the repository's **Actions** tab and open the latest run.
2. You should see two green jobs: **Test, build, scan, SBOM** and **Publish, sign, verify**.
3. In the run's **Artifacts** section you will find the SBOM and the Trivy report.
4. On the repository home page, open **Packages** (right sidebar) to see the image.
5. The summary of the publish job shows the image name and its digest (`sha256:...`).

## 6. Verify a published image yourself

Use a recent version of Cosign. Replace `OWNER`, `REPOSITORY` and `DIGEST` with your real values:

```bash
cosign verify \
  --certificate-identity "https://github.com/OWNER/REPOSITORY/.github/workflows/secure-pipeline.yml@refs/heads/main" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/OWNER/REPOSITORY@sha256:DIGEST
```

A new GHCR package is **private** by default. If you are verifying from a machine that is
not logged in, either run `docker login ghcr.io` first, or make the package public in
**Package settings → Danger Zone → Change visibility**.

## 7. Prove the release gate works

A security gate you have never seen fail is a gate you cannot trust. Follow
**Phase 6** in `docs/IMPLEMENTATION_GUIDE.md` to open a pull request that is
deliberately blocked, without touching `main`.

## Security notes

- Pull requests cannot publish or sign: the publish job is skipped for them, and
  the read-only job has no write or OIDC permission.
- Keyless signing uses a short-lived GitHub OIDC identity. There is **no
  long-lived private signing key** to steal or leak.
- Every third-party GitHub Action is pinned to a full commit SHA, and the Trivy
  binary is pinned to an explicit version. This matters: in March 2026 the
  Trivy GitHub Actions and a Trivy release were compromised through mutable version
  tags. SHA pinning is the defence. Dependabot (`.github/dependabot.yml`) proposes updates
  so the pins do not go stale. Review those PRs.
- The gate blocks fixable CRITICAL findings. An image with zero CRITICAL findings is
  **not** necessarily free of vulnerabilities.
- A valid signature proves *who built and signed* the image. It does not prove the
  application is safe.

## Troubleshooting

**Publish job: "denied" or "permission_denied" when pushing to GHCR**
Check that the job `publish-sign` still has `packages: write`. If the package already
exists from an older attempt and was created by someone else, open the package
settings and give this repository **Write** access under *Manage Actions access*.

**Cosign: "no OIDC token" / "id-token" error**
The `publish-sign` job must have `id-token: write`. Do not remove it.

**Cosign verify says the identity does not match**
The identity is tied to the exact repository, workflow file name and branch. The file must
stay at `.github/workflows/secure-pipeline.yml`, and the run must be a push to `main`.

**Trivy fails with `TOOMANYREQUESTS` / cannot download the vulnerability DB**
This is a rate limit on the public DB registry, not a problem in your project. Click
**Re-run failed jobs** after a few minutes.

**Trivy blocks the image**
Open the Trivy output. Look at the package, installed version and fixed version. Update
the dependency in `requirements.txt` or move to a newer base image in the `Dockerfile`.

**Local `docker build` fails**
Make sure Docker is running and that you are in the project root (where the `Dockerfile` is).

## Project boundary

SecureShip secures the **container delivery path**. It is not a runtime threat
detection system, a complete vulnerability management platform, or a guarantee that
every signed image is secure.
