# Implementation Guide

A step-by-step path from the extracted ZIP to a working, verified pipeline.
Do the phases in order. Each phase ends with a "You should see" line so you know it worked.

---

## Phase 1: Run and test locally

1. Install Python 3.12+ and Docker.
2. Open a terminal in the `secureship` folder.
3. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```
4. Install dependencies: `pip install -r requirements-dev.txt`
5. Run the tests: `pytest -q`
6. Start the API: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
7. In a browser, open http://127.0.0.1:8000/ , create a shipment, then click
   **Advance status** until it shows *Delivered*.
8. Also open `/health`, `/api/v1/status` and `/docs`.

**You should see:** `20 passed`, a working web page where a shipment moves from
*Created* to *Delivered*, and JSON with HTTP 200 from `/health` and `/api/v1/status`.

## Phase 2: Build and run the container

1. Build: `docker build -t secureship-api:local .`
2. Run with hardened settings:
   ```bash
   docker run --rm -p 8000:8000 --read-only --cap-drop ALL \
     --security-opt no-new-privileges secureship-api:local
   ```
3. Open http://127.0.0.1:8000/ (the app) and http://127.0.0.1:8000/health.
4. In another terminal, confirm the container is not root:
   `docker run --rm --entrypoint id secureship-api:local`

**You should see:** the web app loads, you can create a shipment, `/health` returns
`{"status":"healthy"}`, and the user is `uid=10001(appuser)`.

## Phase 3: Run the security tools locally (optional)

1. Install Trivy from its official documentation.
2. Run `make scan`. It fails only on fixable CRITICAL findings.
3. Read any findings. Fix them; do not blindly suppress.
4. Install Syft from its official documentation.
5. Run `make sbom`, then open `sbom.spdx.json` and confirm `fastapi` and `uvicorn` are listed.

**You should see:** a scan result, and an SBOM file listing your dependencies.

## Phase 4: Publish to GitHub

1. Create a **lowercase** empty repository, for example `secureship`.
2. Push the project to the `main` branch. Quick way: `./scripts/push-to-github.sh YOUR-USERNAME`.
   Manual way:
   ```bash
   git init
   git add .
   git commit -m "Initial SecureShip implementation"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/secureship.git
   git push -u origin main
   ```
3. Open the repository's **Actions** tab and click the running workflow.
4. Watch the **Test, build, scan, SBOM** job.

**You should see:** the first job turn green. If it fails, open the failed step and read
the message before changing anything.

## Phase 5: Confirm delivery and signing

No extra settings or secrets are needed. The permissions are declared in the workflow.

1. After job 1 is green, the **Publish, sign, verify** job starts automatically.
2. Open that job. The steps *Publish approved image*, *Sign image digest* and
   *Verify image signature* must all be green.
3. On the repository home page, open **Packages** and confirm the image is listed.
4. Open the job summary and copy the digest (`sha256:...`).
5. (Optional) Verify it yourself: `./scripts/verify-image.sh YOUR-USERNAME/secureship sha256:DIGEST`.

**You should see:** a green verify step, and the image under Packages.

## Phase 6: Prove the release gate works

Goal: show that a vulnerable image is **blocked** and never published. You do this on a
throwaway branch and a pull request, so `main` is never touched.

> Shortcut: `./scripts/demo-gate.sh start` does steps 1 to 3 for you, and
> `./scripts/demo-gate.sh cleanup` does step 8's cleanup. The manual steps are below.

1. Create a branch:
   ```bash
   git checkout -b demo/vulnerable-dependency
   ```
2. Add one old, known-vulnerable package to the **end** of `requirements.txt`:
   ```text
   django==2.2.0
   ```
   (Django 2.2.0 has known CRITICAL vulnerabilities that were fixed in later releases.
   It installs fine and is never imported by the app.)
3. Commit and push the branch:
   ```bash
   git add requirements.txt
   git commit -m "demo: add vulnerable dependency to test the gate"
   git push -u origin demo/vulnerable-dependency
   ```
4. On GitHub, open a **pull request** from that branch into `main`.
5. Open the PR's checks and watch the **Test, build, scan, SBOM** job.
6. Open the failed step **Trivy release gate** and read which package and CVE blocked it.
7. Confirm the **Publish, sign, verify** job did **not** run for the PR.
8. Take a screenshot for your portfolio, then **close the PR without merging** and delete
   the branch.

**You should see:** the gate step red, the publish job skipped, and nothing new in Packages.

Never merge the demo branch into `main`.

---

## Completion checklist

- [ ] `pytest -q` passes locally (20 tests).
- [ ] Docker image builds, the web app loads and `/health` responds.
- [ ] Container runs as non-root (`uid=10001`).
- [ ] Trivy report artifact is kept on each run.
- [ ] Syft SPDX SBOM artifact is kept on each run.
- [ ] Pull requests run job 1 only and cannot publish or sign.
- [ ] Push to `main` publishes to GHCR after passing the gate.
- [ ] Cosign signs the image digest.
- [ ] Cosign verifies against the fixed workflow identity.
- [ ] A demo pull request was blocked by the release gate.
