# SecureShip Security Policy

## Release rule

Publication is blocked when Trivy reports **at least one CRITICAL vulnerability that
has a fix available** in the built image (OS packages or Python libraries).

- The gate is a CI step using Trivy's non-zero exit code.
- Unfixed findings (no patch exists yet) do not block, because there is nothing
  the team can do about them. They still appear in the report.
- A separate informational report lists **HIGH and CRITICAL** findings and is kept
  as a workflow artifact for 30 days.

## Why this is only a starting policy

Severity alone does not describe risk. A production policy should consider whether
the vulnerability is exploitable in this deployment, whether the affected code is
reachable, and the impact of the workload.

## Exceptions

An exception should record:

- Vulnerability ID (for example a CVE number)
- Affected package and image digest
- Reason it is temporarily accepted
- Risk owner and approver
- Compensating control, if any
- Expiry or review date

Never suppress findings globally just to get a green pipeline.

## Pipeline supply-chain rules

- Third-party GitHub Actions are pinned to **full commit SHAs**, never to mutable tags.
- The Trivy version is pinned explicitly.
- Dependabot proposes updates; a human reviews each one before merging.
- Application dependencies are pinned to exact versions.

## Signing policy

Only the `publish-sign` job, running for a push to `main`, signs images. Signing is
keyless (GitHub Actions OIDC). Verification checks **both** the certificate identity
and the OIDC issuer.

A valid signature establishes the signing identity under the configured trust
policy. It does not certify that the image has no vulnerabilities.
