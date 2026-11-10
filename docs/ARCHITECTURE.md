# SecureShip Architecture

## Purpose

SecureShip protects the path from source code to a distributable container image.
The sample app, a small shipment tracker, exists only to give the pipeline a real,
testable artifact.

## The sample application

```text
Browser  --->  static page (index.html + app.js + style.css)
                    |  fetch() to same origin
                    v
               FastAPI (app/main.py)  --->  validation (schemas.py)
                                      --->  in-memory store (store.py)
```

- **Frontend:** plain HTML, CSS and JavaScript. No CDN and no framework, so the page can run
  under `Content-Security-Policy: default-src 'self'`. User text is written to the page with
  `textContent`, never `innerHTML`.
- **Backend:** create, list, track and advance shipments. Input is validated and size-limited,
  tracking codes are random (`secrets`), and the store is capped at 500 shipments.
- **Storage:** memory only. Nothing is written to disk, so the container runs read-only.

## Logical flow

```text
GitHub source (push / pull request)
    |
    v
JOB 1: build-scan                      (read-only; runs for PRs and pushes)
    |-- pytest
    |-- docker build
    |-- Trivy report  (HIGH + CRITICAL, informational, kept as artifact)
    |-- Trivy GATE    (fixable CRITICAL => pipeline stops here)
    |-- Syft SBOM     (SPDX JSON, kept as artifact)
    '-- save approved image  (push to main only)
    |
    |  only for push to main, only if JOB 1 passed
    v
JOB 2: publish-sign                    (packages: write, id-token: write)
    |-- load the exact image that passed the gate
    |-- push to GHCR (tag = commit SHA)
    |-- read the pushed digest (sha256:...)
    |-- Cosign keyless sign of the digest
    '-- Cosign verify against a fixed workflow identity
```

## Trust boundaries

- **Pull-request code is untrusted.** The PR path only ever runs JOB 1, which has
  `contents: read` and nothing else: no package write, no OIDC token.
- **Only JOB 2 holds powerful permissions**, and it runs only for a push to `main`
  after JOB 1 succeeded.
- **What is scanned is what is shipped.** JOB 1 saves the scanned image; JOB 2 loads that
  same image instead of rebuilding it.
- **The digest is the identity.** The tag (commit SHA) is a label; the signature
  is made over `image@sha256:...`.
- **Verification uses a fixed policy:** this repository, this workflow file, the
  `main` branch, and the GitHub Actions OIDC issuer.
- **Pipeline tooling is pinned.** Third-party actions use full commit SHAs and Trivy
  uses an explicit version, so a moved or poisoned tag cannot silently change what runs.

## Container hardening

- Non-root user (uid 10001), no home directory, no login shell.
- Minimal runtime dependencies (no `uvicorn[standard]` extras).
- Server version header disabled; basic security headers added by the app.
- Recommended run flags (used by `make docker-run`): `--read-only`, `--cap-drop ALL`,
  `--security-opt no-new-privileges`.

## Limitations

The gate blocks fixable CRITICAL findings. This is a practical demonstration policy,
not a universal risk model. A production policy should also weigh exploitability,
package reachability, exception ownership and remediation deadlines.
