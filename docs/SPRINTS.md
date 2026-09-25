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

**Status:** Complete — merged in PR #22.


### Sprint 4 — Public Garden Snapshot

**Outcome:** Make public share links useful while keeping private garden history and controls private.

**Acceptance criteria:**
- Public pages show garden name, device type, pod position, plant name, current status, and growing age.
- Public pages include the same read-only pod-status counts used on the owner view.
- Public pages clearly identify themselves as shared/read-only.
- Pod notes, note photos, and editing controls are never rendered on the public page.
- Disabled/non-public share links return not-found behavior.
- No new write endpoints or schema changes are introduced.
- Automated tests verify visible public data and private-data exclusion.
- README and sprint documentation are updated.

**Branch:** `feature/public-garden-snapshot`

**Status:** Complete — merged in PR #23.


### Sprint 5 — Garden List Summaries

**Outcome:** Make the My Gardens page useful as a dashboard when an account has multiple gardens.

**Acceptance criteria:**
- Each garden card shows total pod count, active pod count, and harvesting pod count.
- Active excludes Empty and Removed pods.
- Each card shows whether the garden is Public or Private.
- Each card shows the latest pod activity timestamp when available.
- Summary data is calculated only for gardens owned by the authenticated user.
- The view prefetches pods to avoid per-card pod queries.
- Automated tests verify counts, visibility, and owner isolation.
- README and sprint documentation are updated.

**Branch:** `feature/garden-list-summaries`

**Status:** Complete — merged in PR #24.


### Sprint 6 — API Ownership Hardening

**Outcome:** Make REST API access enforce the same privacy and ownership boundaries as the web application.

**Acceptance criteria:**
- Garden, pod, and pod-note APIs require authentication.
- Authenticated users can list/read/write only their own non-guest garden data.
- Pod creation is rejected when the parent garden belongs to another user.
- Pod-note creation is rejected when the parent pod belongs to another user's garden.
- Cross-user retrieve/update/delete attempts return not-found behavior for garden data.
- Global notes remain publicly readable but can only be edited/deleted by their author.
- API tests cover authentication, owner isolation, cross-parent creation, and global-note author permissions.
- README and sprint documentation are updated.

**Branch:** `security/api-ownership-hardening`

**Status:** Complete — merged in PR #25.


### Sprint 7 — Environment Port and Developer API Paywall

**Outcome:** Make deployment port selection configurable through environment files and establish a billing-provider-neutral entitlement boundary for paid developer API access.

**Acceptance criteria:**
- Development Compose publishes the app using `APP_PORT` from `.env`, defaulting to 8000.
- Production Compose publishes nginx using `APP_PORT`, defaulting to 80.
- `.env.example` and `.env.prod.example` document the port setting.
- The developer API paywall is disabled by default and controlled by `API_PAYWALL_ENABLED`.
- Developer API entitlement records support plan, subscription status, provider identifiers, and optional expiration.
- When the paywall is enabled, API viewsets reject users without an active entitlement.
- Active entitlements allow API access; expired/past-due entitlements do not.
- Staff/superusers retain administrative API access.
- Billing-provider integration is documented as a webhook-driven entitlement update flow.
- Regression tests cover port configuration and entitlement behavior.
- README and developer API documentation are updated.

**Branch:** `feature/env-port-developer-paywall`

**Status:** Complete — merged in PR #26.


### Sprint 8 — Optional Async Email Runtime

**Outcome:** Make the documented Redis-backed Celery email path runnable through Docker Compose without changing the default synchronous behavior.

**Acceptance criteria:**
- Celery installs with Redis transport support.
- Development Compose provides optional Redis and Celery worker services under the `async-email` profile.
- Production Compose provides optional Redis and Celery worker services under the same profile.
- The web service receives `CELERY_BROKER_URL` from environment configuration.
- Production Redis persists broker data in a named volume.
- With no broker configured, synchronous email remains the default.
- Environment examples document how to enable the profile.
- Regression tests verify dependency and Compose wiring.
- README and sprint documentation are updated.

**Branch:** `feature/optional-async-email-runtime`

**Status:** Complete — merged in PR #27.


### Sprint 9 — Guest Garden Account Claim

**Outcome:** Preserve guest progress when a visitor creates or signs into an account.

**Acceptance criteria:**
- A guest garden tied to the current browser token is transferred to the authenticated user after login.
- Immediate registration claims the current guest garden.
- Email-confirmation activation claims the current guest garden after the account is activated.
- Claimed gardens clear guest ownership metadata and become normal account gardens.
- Existing pods, plant data, notes, and photos remain attached through the claim.
- The guest cookie is cleared after a successful claim.
- A user without the matching guest cookie cannot claim another browser's guest garden.
- Automated tests cover login, registration, history preservation, and token isolation.
- README and sprint documentation are updated.

**Branch:** `feature/claim-guest-garden`

**Status:** In review.
