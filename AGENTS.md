# Repository workflow

- Commit each small, coherent implementation step rather than accumulating unrelated changes.
- Before each code commit, add rigorous tests for the introduced or changed behavior and run the relevant tests, existing checks and directly affected regressions. Commit only working changes with passing checks.
- Failed, blocked, skipped or uncollected required acceptance cases are not passes. Keep unfinished features explicitly unavailable and record prerequisites; never claim scientific acceptance from isolated unit tests.
- Follow `backendplan.md` and `docs/frontend_api_contract.md`. Do not follow the superseded gap-analysis roadmap.
- Keep credentials, local services, raw farmer records and generated acceptance artifacts out of commits. Preserve existing user work and browser records.
