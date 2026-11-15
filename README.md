# Space-Apps-challenge
The Hollows to the Nasa Space Apps Challenge

## Current release: restored UI and private plots

The original `b59a73f` satellite cockpit, drawing controls and theme are restored,
with private accounts and backend-saved KML preview/confirmation. Backend code
`e221e98` and frontend code `e46343d` are hosted separately on Tailscale ports
8080/1080. AI remains unavailable pending a real field-to-model pipeline. See the
[UI comparison and delivery plan](docs/merger/09-ui-restoration.md).
That document records the actual release gates, runtime layout and remaining
feature plans. Nothing has been pushed. This supersedes the shared-access target
of the historical release below.

## Historical shared release: separate frontend and backend

**Milestones A and B are implemented and committed locally:** shared profiles,
existing field/evidence reads, field editing, durable import jobs and geometry
exports. The applications remain separate; AI/model and economics are excluded.

Start with the [implementation handoff](docs/merger/08-implementation.md) for the
exact release pair, evidence and limitations, then the
[shared-mode runbook](docs/merger/07-runbook.md) for its configuration and startup.
Backend branch `backend` is checked out at
`Space-Apps-challenge\.local\integration-backend`; the original checkout remains
on the concurrently used `backend-ai` branch. Frontend branch `frontend` is in
`Space-Apps-challenge-frontend`. The concurrent original backend and donor
checkouts remain untouched by the private rollout.

## Restarted integration plan - 2026-11-15

**Keep frontend and backend as two separate applications.** This revision
replaces the earlier monorepo proposal and re-audits the current implementations,
including the second frontend worktree inside the backend folder.

The main frontend already matches the shared field/evidence API in
`Space-Apps-challenge`. The named backend checkout and its nested frontend
implement a different, authenticated profile slice. The agreed target is to
preserve account-free shared access and adapt that profile functionality into
the existing shared API/UI, not run two incompatible backends.

1. [Fresh implementation audit and incompatibilities](docs/merger/01-audit.md)
2. [Two-instance architecture and reuse decisions](docs/merger/02-architecture.md)
3. [Actual contracts and proposed shared-profile bridge](docs/merger/03-contract.md)
4. [Implementation sequence, files, and dependencies](docs/merger/04-delivery-plan.md)
5. [Evidence, regression cases, and release gates](docs/merger/05-acceptance.md)
6. [Confirmed decisions, risks, and handoff](docs/merger/06-decisions.md)
7. [Independent startup and integration runbook](docs/merger/07-runbook.md)
8. [Implemented release pair and acceptance handoff](docs/merger/08-implementation.md)
9. [Current private UI/KML release and missing-feature plans](docs/merger/09-ui-restoration.md)

Documents 01-06 preserve the restarted planning/audit snapshot. Its proposed
profile and field/import/export increments have now been implemented; manual
plans, AI/model and economic work remain deferred. Documents 07-08 preserve the
shared release; document 09 describes the current private release.

This branch changes documentation only. The earlier plan remains in commit
`f1ec64f`; its findings are not the current implementation baseline. Local
working changes, source commits and contract hashes are distinguished below.
