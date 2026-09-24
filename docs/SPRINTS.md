# Sprint Process

Smart Garden uses small, reviewable sprints to keep product work, maintenance, testing, and documentation moving together.

## Goals

Each sprint should:

- deliver one coherent user-facing improvement or engineering outcome;
- keep changes small enough to review and test confidently;
- include tests and documentation in the same sprint when behavior changes;
- leave `main` deployable and CI-green;
- avoid carrying undocumented work or hidden follow-up requirements.

## Sprint lifecycle

1. **Plan**
   - Define the user/problem outcome.
   - List acceptance criteria.
   - Identify security, data-migration, compatibility, and deployment risks.
   - Keep scope small enough for one focused PR when practical.

2. **Readiness**
   - Confirm the current `main` branch is green.
   - Check open PRs/issues for conflicts or overlapping work.
   - Confirm local Docker Compose and test commands still represent the supported development path.

3. **Implement**
   - Branch from the latest `main`.
   - Make focused changes.
   - Add or update tests with the implementation.
   - Update docs and examples when behavior or configuration changes.

4. **Verify**
   - Run Django system checks.
   - Run the full automated test suite.
   - Exercise the changed workflow locally when practical.
   - Review CI logs, not only the final green/red status.

5. **Review and merge**
   - Open a PR with a concise summary and testing notes.
   - Fix failures on the same branch.
   - Merge only after required CI checks pass.

6. **Close**
   - Update the sprint/backlog documentation.
   - Record significant architectural or operational decisions.
   - Move directly to the next prioritized sprint unless a blocker requires attention.

## Definition of Ready

A sprint item is ready when:

- the desired outcome is clear;
- acceptance criteria are testable;
- dependencies and obvious risks are identified;
- there is no unresolved conflicting PR;
- required credentials/services are either available or explicitly out of scope.

## Definition of Done

A sprint item is done when:

- implementation is complete;
- authorization/security behavior is covered where relevant;
- tests cover the new behavior and important failure paths;
- `python manage.py check` passes;
- the full Django test suite passes;
- Docker/local-development behavior remains valid when affected;
- documentation is updated;
- CI is green;
- the PR is merged.

## Branch and PR naming

Prefer descriptive branches:

- `feature/<short-description>`
- `fix/<short-description>`
- `test/<short-description>`
- `docs/<short-description>`
- `ci/<short-description>`
- `refactor/<short-description>`

PR titles should describe the delivered outcome, not the implementation activity.

## Baseline development cycle

Formal sprint documentation was introduced after the following work had already been completed. These PRs form the current baseline:

- PR #12 — guest-flow and import/export regression coverage.
- PR #13 — multipart registration email templates.
- PR #14 — production email-provider configuration.
- PR #15 — optional Celery email delivery.
- PR #16 — stable session-secret behavior.
- PR #17 — CI warning cleanup and Django checks.
- PR #18 — garden edit/delete lifecycle controls and global message rendering.

Future product work should be recorded here or in linked GitHub issues before or during implementation.


## Active sprint history

### Sprint 1 — Pod Note Lifecycle

**Outcome:** Let garden owners and guest-garden users correct or remove pod notes without leaving the garden side panel.

**Acceptance criteria:**
- Notes can be edited inline from the pod side panel.
- Notes can be deleted only through an explicit POST action with confirmation in the UI.
- Existing note photos remain available when only text is edited.
- Deleted notes remove their attached image from storage when present.
- Owner/guest authorization is enforced server-side through the garden access rules.
- Cross-user note modification returns not-found behavior.
- Deleting a guest note immediately restores one unit of the guest note quota.
- Automated regression tests cover owner, guest, cross-user, and method restrictions.
- README and sprint documentation are updated.

**Branch:** `feature/pod-note-lifecycle`

**Status:** Complete — merged in PR #20.


### Sprint 2 — Pod Planting Actions

**Outcome:** Make common planting-cycle actions fast and consistent from the pod side panel.

**Acceptance criteria:**
- "Plant Today" saves the current plant name, sets the planted date to today, and sets status to Seeded.
- "Reset Pod" clears plant name, planted date, and status back to Empty.
- Reset preserves existing pod notes and photos as historical context.
- Reset requires explicit confirmation in the UI.
- Account-owner and guest-token authorization continue to be enforced server-side.
- Cross-user attempts return not-found behavior.
- Automated tests cover account, guest, and unauthorized usage.
- README and sprint documentation are updated.

**Branch:** `feature/pod-planting-actions`

**Status:** Complete — merged in PR #21.


### Sprint 3 — Garden Status Overview

**Outcome:** Make the state of the entire garden understandable at a glance without opening each pod.

**Acceptance criteria:**
- Garden detail shows counts for every supported pod status: Empty, Seeded, Sprouted, Growing, Harvesting, and Removed.
- The overview is derived from the already-loaded pod collection and requires no schema change.
- The total pod count is visible alongside the status breakdown.
- Grid fallback cards display each pod's current status.
- The overview works for both account-owned and guest gardens.
- Automated tests verify status counts and guest behavior.
- README and sprint documentation are updated.

**Branch:** `feature/garden-status-overview`

**Status:** In review.
