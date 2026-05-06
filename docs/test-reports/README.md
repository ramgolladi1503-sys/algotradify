# Test Reports — Algotradify

## Current CI gate

The repository includes a GitHub Actions workflow:

```text
.github/workflows/portfolio-ci.yml
```

This workflow validates the project as a recruiter-facing SDET/API/WebSocket testing portfolio.

## What the CI checks today

- README exists.
- Architecture SVG exists.
- SDET one-pager exists.
- README includes problem statement, architecture, test strategy, failure modes, and roadmap.
- A Markdown CI report artifact is generated on each run.

## Why this matters

This project is meant to show practical testing of live runtime systems. The current gate proves the repo has the minimum portfolio assets. The next step is actual runtime tests around FastAPI, WebSockets, Redis degradation, and UI states.

## Next test-report upgrades

- FastAPI endpoint contract test report.
- WebSocket payload-shape test report.
- Redis unavailable regression report.
- Frontend empty/error state report.
- Local stack smoke-test report.
- Playwright trace and screenshot report.
