# Security Policy

## Reporting a vulnerability

Please report security issues privately, not as a public issue.

Use GitHub's private reporting form:
**[Report a vulnerability](https://github.com/HerrStolzier/beattrack/security/advisories/new)**

That opens a private thread visible only to the maintainer. It is the only
channel — there is no separate security mailing address.

If you cannot use the form, open a public issue that says only that you have a
security report and would like a private channel. Please do not include details.

### What helps

- What an attacker can do, not only which pattern looked wrong.
- The smallest request or input that shows it.
- Which part is affected: the API (`apps/api`), the web app (`apps/web`), or the
  hosted site at beattrack.app.

### What to expect

This is a single-maintainer hobby project, so please calibrate accordingly:

- An acknowledgement within about a week.
- An honest answer about whether it will be fixed, and roughly when. "Not worth
  fixing" is a possible answer, and you will be told why.
- Credit in the advisory if you want it.

There is no bug bounty and no guaranteed response time.

## Scope

**In scope**

- Code in this repository.
- The hosted instance at beattrack.app and its API.

**Out of scope**

- Findings in third-party services the project depends on (Supabase, Vercel,
  Hetzner, Deezer, Spotify, SoundCloud, Apple Music, AcoustID). Report those to
  the service.
- Missing hardening headers or rate limits with no demonstrated impact.
- Automated scanner output pasted without a working scenario.

## Testing against the live site

Please stay gentle: no load or denial-of-service testing, no automated scanning
that generates significant traffic, and no attempts to reach other people's
data. A single proof-of-concept request is fine.

If you need to test something noisy, run the stack locally. Setup instructions
are in the [README](README.md).

## Supported versions

The project has no tagged releases. Only the current `main` branch is supported;
fixes land there and deploy from there.

## What already runs

Automated checks on every pull request and on a weekly schedule:

| Tool | Covers |
| --- | --- |
| CodeQL | This repository's own TypeScript and Python code |
| Dependabot | Dependency vulnerabilities and version updates |
| gitleaks | Secrets in commits, plus GitHub push protection |
| Trivy | Container base images and Dockerfiles |
| pip-audit | Python dependencies, as a blocking CI step |

These catch the routine cases. They are not a substitute for a human finding a
real logic flaw, which is why this policy exists.
