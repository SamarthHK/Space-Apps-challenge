# 06. Decisions, open details and handoff

## Confirmed in this request

- Restart planning from the changed built solutions, not the earlier snapshot.
- Keep frontend and backend as two separate instances.
- Access model explicitly selected: **"Keep the current account-free shared
  workspace; adapt profile persistence to it."**
- This task updates planning documents; it does not authorize implementation,
  source-branch overwrites, database/user-data migration or public deployment.
- AI/model work remains outside the continued merger-planning scope.

The earlier proposed login baseline and monorepo prefix imports are superseded.
No new login/identity provider decision is needed for this integration.

## Recommended implementation decisions

| Decision | Recommendation / reason | Remaining detail |
| --- | --- | --- |
| Code baseline | A shared API + F current UI, because their actual contracts match | Backend owner publishes its required dirty dependency closure |
| Donor reuse | Adapt B profile validation/revisions and P profile form only | Review field-level extraction and preserve source attribution |
| Shared profile | New stable workspace-owned record, empty at provisioning | Operator supplies workspace ID; choose final application-schema name |
| Scope | Profile applies to configured workspace, not each browser or transient project list | Define explicit workspace/project mapping and future multi-workspace behavior before adding it |
| Concurrency | Shared contract's strong ETag/If-Match, not donor body-version wire format | Freeze exact malformed-header error/ETag syntax and document client handling |
| Database | Preserve canonical schema; separate application migration ledger/writer | Select target DB/roles and perform controlled prepared-data transfer only if necessary |
| Network | Existing loopback/Tailscale allow-list; frontend 1080/API 8000 by configured default | Actual hosts, port availability, deployment and test origin allow-lists |
| Runtime | One backend package/environment; current F npm build independently | Resolve supported Python/lock and prove native dependencies in clean environment |
| Publication | Reviewed backend/frontend release pair with exported contract hash | Branch/remote handoff by owners; no force-push over divergent local history |

These are scoped recommendations for implementation, not additional application
changes made by this documentation branch.

## Blocker ledger

| Blocker | Evidence | Next action / owner |
| --- | --- | --- |
| Dirty canonical prerequisites | A read API expects migration 005's views/tables; canonical/identity files untracked during audit | Backend owner publishes tested preparation closure; do not cherry-pick only API commits |
| Incomplete local A test environment | Missing `pluggy`; foundation passed only through separate existing interpreter | Reproduce/repair chosen release environment in an isolated checkout, not someone else's active environment |
| Shared profile absent | A capability not implemented; B requires user/session ownership | Implement T2-T5 adaptation rather than route alias/proxy |
| Write transport absent | A/F read-only CORS/client/header handling | Add profile-specific mutation handling and browser preflight gate |
| Current live data availability unverified | This audit did not start/query prepared DB or production services | T1 verifies actual scoped DB/schema/corpus; health alone is insufficient |
| Source work continuing concurrently | Additional A model/outcome/config/lock files appeared during inspection | Use source-pinned handoff; exclude unrelated model scope and re-audit changed dependencies only |
| Conflicting execution documents | Old source-plan sections and donor runbook target different builds | Replace stale status/commands in owning source branches during handoff |

## Privacy and data handling

Shared access means every permitted client can view/edit the shared profile.
Make that visible in the UI before profile entry. Do not automatically publish
the donor's real private profile records or import old browser data. An account-
free application must not imply per-user privacy or attribution.

Tailnet access policy is the access boundary, not CORS. No wildcard/public bind,
Funnel, public reverse proxy or port forwarding for this mode. Do not add
username/password prompts merely to reuse donor code. Public/multi-user
deployment is a separate future decision requiring a new authorization design.

## Scope boundaries

Milestone A joins existing read and profile capabilities. Milestone B adds
field drawing/import/export. Later soil/catalog/manual-plan work is a distinct
extension, not evidence that currently absent features are built.

Model/training/inference, recommendation ranking, financial scenarios, market
pricing and forecast source work are not dragged into Milestone A. Keep their
existing unavailable states. No "accept all pending observations" shortcut or
browser financial fallback is permitted.

## Handoff checklist

Before coding, assign owners to T0-T6 and publish the source-pinned baseline.
Include the selected workspace/schema/role/origin configuration without secrets,
the generated contract hash, actual data prerequisites and rollback procedure.

The merger documents are coordination material, not a competing OpenAPI source.
Backend owns implemented schemas; frontend pins the released artifact. Read
the files actually used by the chosen runtime rather than inferring architecture
from a folder/branch name or a historical progress claim.

Preserve original checkouts, nested worktree, user data and migration history.
Publishing the local planning branch or creating a pull request is a separate
action from updating/committing these Markdown files.
