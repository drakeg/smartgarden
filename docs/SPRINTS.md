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

**Status:** Complete — merged in PR #29.


### Sprint 10 — Garden Search and Filters

**Outcome:** Make larger garden collections easy to navigate from My Gardens.

**Acceptance criteria:**
- My Gardens supports case-insensitive name search through the `q` query parameter.
- Users can filter by Public or Private sharing state.
- Search and visibility filters can be combined.
- Invalid visibility values safely fall back to showing all sharing states.
- Filtering remains scoped to gardens owned by the authenticated user.
- Existing pod summary prefetch/count behavior remains intact.
- The UI shows active filter values, a matching result count, and a clear-filter action.
- Empty filtered results are distinguished from an account with no gardens.
- Automated tests cover combined filters, owner isolation, and invalid values.
- README and sprint documentation are updated.

**Branch:** `feature/garden-search-filters`

**Status:** Complete — merged in PR #30.


### Sprint 11 — API Parent Reassignment Authorization

**Outcome:** Prevent authenticated API callers from moving existing pods or notes into gardens they do not own.

**Acceptance criteria:**
- API pod updates reject garden reassignment to another user's or a guest garden.
- API pod-note updates reject reassignment to a pod in another user's or a guest garden.
- Rejected updates leave parent relationships and existing data unchanged.
- Reassignment between the caller's own account gardens or pods remains supported.
- Existing create-time ownership restrictions remain intact.
- Regression tests cover rejected cross-user/guest moves and valid owner moves.
- README and sprint documentation are updated.

**Branch:** `security/api-parent-reassignment`

**Status:** Complete — merged in PR #31.


### Sprint 12 — Redis 8 Runtime Refresh

**Outcome:** Refresh the optional async-email broker runtime to Redis 8 on the latest main branch without carrying forward a stale dependency PR.

**Acceptance criteria:**
- Development async-email Compose profile uses `redis:8-alpine`.
- Production async-email Compose profile uses `redis:8-alpine`.
- Existing Redis health checks, persistence, and Celery broker wiring remain unchanged.
- Regression tests ensure both Compose files stay on Redis 8 and do not drift back to Redis 7.
- README documents the Redis 8 runtime.
- The stale Renovate Redis 8 PR is superseded by the fresh current-main PR.

**Branch:** `maintenance/redis-8-refresh`

**Status:** Complete — merged in PR #32.


### Sprint 13 — Developer API Plan Rate Limits

**Outcome:** Make Starter, Pro, and Enterprise developer plans operationally distinct by enforcing configurable per-user API request limits.

**Acceptance criteria:**
- Plan throttling activates only when `API_PAYWALL_ENABLED=True`.
- Starter, Pro, and Enterprise each have independently configurable rates.
- Default rates are Starter `100/hour`, Pro `1000/hour`, and Enterprise `5000/hour`.
- Active developer users receive HTTP 429 after exceeding their plan rate.
- Higher tiers can sustain more requests when configured with higher rates.
- Staff and superusers bypass developer throttling.
- Disabling the paywall also disables plan throttling.
- Rate configuration is documented in development and production environment examples.
- Regression tests cover exhaustion, tier differences, staff bypass, and disabled-paywall behavior.
- README and developer API documentation are updated.

**Branch:** `feature/developer-api-rate-limits`

**Status:** Complete — merged in PR #33.


### Sprint 14 — Shared Developer API Throttle Cache

**Outcome:** Use one shared Redis-backed rate-limit counter across production web workers instead of independent in-memory counters.

**Acceptance criteria:**
- A dedicated developer API cache alias uses Redis when configured.
- Production with the developer paywall enabled requires a shared cache URL.
- Development without a cache URL retains local-memory behavior.
- Redis can be started through an optional `api-paywall` Compose profile.
- Development and production environment examples document the shared cache URL.
- Existing per-plan and staff-bypass behavior remains intact.
- Tests cover dedicated cache use and shared allowance across API endpoints.
- Developer API docs explain operational rollout and concurrent-throttling limitations.

**Branch:** `fix/shared-developer-api-throttle-cache`

**Status:** Complete — merged in PR #34.


### Sprint 15 — Developer API Access Status

**Outcome:** Give authenticated developers a safe self-service endpoint for understanding their API entitlement and effective rate.

**Acceptance criteria:**
- `GET /api/developer-access/` requires authentication.
- The endpoint remains reachable even without an active developer entitlement.
- Responses report paywall state, entitlement presence/active state, effective access, plan/status, expiration, request rate, and admin bypass.
- Active plans report their configured effective request rate.
- Expired/inactive entitlements report no effective paid access.
- Disabled-paywall mode reports effective access without a paid rate.
- Staff/superusers report administrative bypass.
- Billing provider/customer/subscription identifiers are never exposed.
- Regression tests cover unauthenticated, missing, active, expired, disabled-paywall, staff, and privacy behavior.
- README and developer API documentation are updated.

**Branch:** `feature/developer-access-status`

**Status:** Complete — merged in PR #35.


### Sprint 16 — Developer API Token Lifecycle

**Outcome:** Let authenticated developers inspect, rotate, and revoke their long-lived DRF API token safely.

**Acceptance criteria:**
- `GET /api/developer-token/` requires authentication and reports only token presence/creation time.
- Existing token values are never re-displayed by the status endpoint.
- Token rotation requires password confirmation.
- Rotation immediately invalidates the previous token and returns the replacement token once.
- Token revocation requires password confirmation.
- Revocation immediately invalidates the current token.
- A stolen API token alone is insufficient to rotate or revoke credentials.
- The existing password-authenticated `/api-token-auth/` endpoint can issue a token again after revocation.
- Regression tests cover authentication, non-disclosure, failed confirmation, rotation, and revocation.
- README and developer API documentation are updated.

**Branch:** `feature/developer-token-lifecycle`

**Status:** Complete — merged in PR #36.


### Sprint 17 — Production Database Configuration Hardening

**Outcome:** Make the production PostgreSQL service and Django application use one consistent environment-driven database configuration and prevent accidental SQLite or hardcoded-password deployments.

**Acceptance criteria:**
- Production Compose reads PostgreSQL credentials from `.env.prod` instead of hardcoded values.
- PostgreSQL health checks verify readiness without hardcoded credentials.
- `DATABASE_URL` remains supported and takes precedence when supplied.
- Without `DATABASE_URL`, production Django builds its PostgreSQL connection from `POSTGRES_*` variables.
- Production refuses to start without a database password when no `DATABASE_URL` is configured.
- Development continues to default to SQLite.
- Production no longer silently falls back to SQLite.
- Regression tests cover environment-driven PostgreSQL, URL precedence, missing credentials, development fallback, and Compose wiring.
- README and production environment documentation are updated.

**Branch:** `fix/production-database-config`

**Status:** Complete — merged in PR #37.


### Sprint 18 — Database Readiness and Startup Ordering

**Outcome:** Distinguish application liveness from database readiness and prevent production migrations from racing PostgreSQL startup.

**Acceptance criteria:**
- `/health/` remains a lightweight liveness endpoint with no database dependency.
- `/ready/` performs a minimal database query and returns HTTP 200 only when the database is reachable.
- Database errors make `/ready/` return HTTP 503 without changing `/health/`.
- Production web startup waits for PostgreSQL's health check before running migrations.
- Production web container health checks use `/ready/`, not the liveness endpoint.
- Regression tests cover ready/unavailable database behavior and Compose startup/health wiring.
- README and sprint documentation are updated.

**Branch:** `feature/database-readiness-check`

**Status:** Complete — merged in PR #38.


### Sprint 19 — Graceful Production Runtime

**Outcome:** Eliminate duplicate startup work and ensure deployment/stop signals reach Gunicorn directly with time to drain in-flight requests.

**Acceptance criteria:**
- Production no longer runs migrations or static collection a second time in the Compose command.
- The image entrypoint remains the single startup path for migrations/static collection.
- The entrypoint `exec`s the configured Gunicorn command so Gunicorn receives container signals directly.
- Production Compose invokes Gunicorn without an intermediate shell.
- Gunicorn has an explicit graceful shutdown timeout.
- Docker's stop grace period is longer than the Gunicorn graceful timeout.
- Regression tests cover single startup execution, direct Gunicorn command, and shutdown timing.
- README and sprint documentation are updated.

**Branch:** `fix/graceful-production-runtime`

**Status:** Complete — merged in PR #39.


### Sprint 20 — Trusted Proxy HTTPS Handling

**Outcome:** Make Django HTTPS detection reliable behind a trusted TLS-terminating proxy without blindly trusting forwarded protocol headers.

**Acceptance criteria:**
- Production proxy trust is explicit and disabled by default in Django settings.
- When enabled, Django treats `X-Forwarded-Proto: https` as a secure request.
- Requests without the trusted HTTPS header continue to redirect when `SECURE_SSL_REDIRECT=True`.
- Nginx preserves an upstream `X-Forwarded-Proto` value when provided.
- Nginx falls back to its own request scheme when no upstream forwarded-protocol header exists.
- The production environment example documents both proxy trust and HTTPS redirect settings.
- Documentation warns against enabling proxy trust for directly exposed, untrusted traffic.
- Regression tests cover Django redirect behavior and Nginx/header configuration.

**Branch:** `fix/trusted-proxy-https`

**Status:** Complete — merged in PR #40.


### Sprint 21 — Production Data Recovery and Persistent Media

**Outcome:** Protect both PostgreSQL data and uploaded pod-note photos from container replacement and provide a repeatable backup/restore path.

**Acceptance criteria:**
- Production uploaded media is stored in a named Docker volume instead of the web container filesystem.
- Nginx serves the shared media volume read-only under `/media/`.
- PostgreSQL backup tooling creates timestamped custom-format dumps using the configured production database credentials.
- PostgreSQL backup output is written atomically and empty dumps are rejected.
- PostgreSQL restore requires explicit confirmation and fails fast on restore errors.
- Media backup tooling creates timestamped compressed archives from the persistent media volume.
- Media restore requires explicit confirmation and overlays archived files without deleting unrelated files.
- Generated backup files are ignored by Git.
- CI validates recovery-script shell syntax.
- Regression tests cover persistent media wiring, Nginx media serving, and backup/restore script safeguards.
- A production recovery runbook documents off-host backup, maintenance-window restore, and post-restore verification.

**Branch:** `ops/postgres-backup-restore`

**Status:** Complete — merged in PR #41.


### Sprint 22 — Backup Verification and Retention

**Outcome:** Make production recovery artifacts easier to trust and safer to retain by coordinating DB/media backups, validating formats before acceptance, and providing guarded local pruning.

**Acceptance criteria:**
- Database and media backup scripts accept a shared timestamp.
- A single backup command creates matching DB/media recovery artifacts.
- PostgreSQL dumps are parsed with `pg_restore --list` before being accepted.
- Media archives are listed with `tar` before being accepted.
- Existing DB/media backup pairs can be verified without restoring them.
- Local retention defaults to 30 days and dry-run behavior.
- Deletion requires explicit `PRUNE_CONFIRM=YES`.
- Retention only matches SmartGarden's timestamped DB/media backup filename patterns.
- CI validates all backup/restore/verification/retention shell scripts.
- Regression tests cover shared timestamps, format verification, and pruning safeguards.
- The recovery runbook documents coordinated backups, verification, local retention, and continued off-host storage requirements.

**Branch:** `ops/backup-verification-retention`

**Status:** Complete — merged in PR #42.


### Sprint 23 — Non-Root Multi-Stage Production Image

**Outcome:** Reduce container attack surface by removing build tools from the runtime image and running the application as an unprivileged user.

**Acceptance criteria:**
- Python dependencies are built in a dedicated builder stage.
- The runtime stage does not include compiler/build-header packages.
- Runtime-only packages remain available for health checks/database connectivity.
- The application runs as a dedicated non-root `smartgarden` user.
- Application, static, and media directories are owned by the runtime user in the image.
- The existing exec-based entrypoint behavior is preserved.
- Existing production volumes have a documented one-time ownership migration path.
- Regression tests prevent drift back to a root runtime or single-stage compiler-bearing image.
- README and sprint documentation are updated.

**Branch:** `security/nonroot-multistage-image`

**Status:** Complete — merged in PR #43.


### Sprint 24 — Developer API Quota Status

**Outcome:** Give developers self-service visibility into the current rolling API rate-limit window without introducing a billing ledger.

**Acceptance criteria:**
- `GET /api/developer-quota/` requires authentication.
- Active paid plans report configured rate, request limit, used requests, remaining requests, and rolling-window duration.
- Exhausted quotas report an approximate retry delay.
- Requests rejected with HTTP 429 do not increase the reported used count.
- The quota-status endpoint itself does not consume plan quota.
- Missing/inactive entitlements report quota as not applicable.
- Disabled-paywall mode reports quota as not applicable.
- Staff/superuser bypass reports quota as not applicable.
- Responses explicitly identify the data as approximate rather than billing-grade usage metering.
- Regression tests exercise the shared throttle cache and exhaustion behavior.
- README and developer API documentation are updated.

**Branch:** `feature/developer-quota-status`

**Status:** Complete — merged in PR #44.


### Sprint 25 — Durable Developer API Usage Metering

**Outcome:** Persist daily paid Developer API usage in PostgreSQL so historical reporting does not depend on Redis throttle history.

**Acceptance criteria:**
- Accepted paid Developer API viewset requests increment a durable daily usage bucket.
- Daily usage buckets are unique per developer, date, and plan.
- Plan is snapshotted so later plan changes do not rewrite historical usage.
- Atomic database increments preserve counts across concurrent workers.
- Usage tracks total requests plus success, client-error, and server-error response classes.
- Authentication failures, entitlement denials, and HTTP 429 throttle rejections are not metered.
- Metering is disabled when the developer paywall is disabled and bypassed for staff/superusers.
- `GET /api/developer-usage/` requires authentication and returns the caller's own durable usage only.
- The history window defaults to 30 days and is bounded to 1–90 days.
- Responses explicitly distinguish durable reporting from invoice-authoritative billing data.
- Regression tests cover metering, throttle exclusion, paywall-disabled behavior, plan changes, and history bounds.
- A schema migration, README, and developer API documentation are included.

**Branch:** `feature/durable-api-usage`

**Status:** Complete — merged in PR #45.


### Sprint 26 — Developer Usage Reporting

**Outcome:** Make durable Developer API usage easy to export and inspect without giving developers or support staff mutation access to metering data.

**Acceptance criteria:**
- `GET /api/developer-usage/export/` requires authentication.
- CSV export is limited to the authenticated developer's own usage.
- CSV export uses the same default 30-day and bounded 1–90 day history window as the JSON endpoint.
- Export includes date, plan, total requests, response-class counts, and last-request timestamp.
- Export excludes billing-provider identifiers and other developers' usage.
- Django admin exposes durable usage for support/reconciliation.
- The admin usage view is read-only and does not allow add/change/delete operations.
- Regression tests cover authentication, ownership isolation, date-window bounds, CSV contents, and read-only admin registration.
- README and developer API documentation are updated.

**Branch:** `feature/developer-usage-reporting`

**Status:** Complete — merged in PR #46.


### Sprint 27 — Developer Self-Service Dashboard

**Outcome:** Consolidate Developer API access, quota, durable usage, export, and credential lifecycle into one authenticated web interface.

**Acceptance criteria:**
- `/account/developer/` requires authentication.
- The dashboard shows paywall state, effective access, entitlement status, plan, expiration, and admin bypass.
- Active paid plans show current shared-cache quota rate, usage, remaining requests, window duration, and retry timing.
- The dashboard shows 30-day durable usage totals and recent daily/plan buckets.
- A CSV export link uses the existing authenticated developer usage export endpoint.
- Existing API token values are never displayed.
- Issuing/rotating a token requires the current account password and returns the new token only in the immediate response.
- Rotating invalidates the previous token immediately.
- Revocation requires the current account password and removes the current token immediately.
- Token-changing forms are POST-only and CSRF-protected.
- The authenticated navigation exposes the Developer Dashboard.
- Regression tests cover authentication, privacy, password confirmation, rotation, first-token issuance, revocation, quota/access rendering, and durable usage rendering.
- README and sprint documentation are updated.

**Branch:** `feature/developer-dashboard`

**Status:** Complete — merged in PR #47.


### Sprint 28 — Complete Garden Backup Export

**Outcome:** Extend garden portability beyond text-only JSON by adding a photo-preserving ZIP backup format without breaking existing JSON exports/imports.

**Acceptance criteria:**
- Existing JSON export/import behavior remains backward-compatible and continues to exclude photo binaries.
- Authenticated garden owners can download a complete ZIP backup containing `garden.json` plus referenced pod-note photos.
- Archive manifests declare an explicit archive format version.
- The existing import page accepts both legacy `.json` exports and complete `.zip` backups.
- ZIP imports restore note text, timestamps, and referenced photos into the new garden.
- ZIP imports reject unsafe traversal/absolute photo paths.
- ZIP imports reject missing referenced photos.
- ZIP imports enforce total uncompressed and per-photo size limits.
- ZIP imports verify image payloads before saving them.
- Garden creation/import is atomic at the database level.
- UI clearly distinguishes legacy JSON export from complete ZIP backup.
- Regression tests cover photo round-trip, JSON compatibility, unsafe paths, missing files, invalid images, and photo size limits.
- README, import UI, garden detail actions, and sprint documentation are updated.

**Branch:** `feature/garden-archive-export`

**Status:** Complete — merged in PR #48.


### Sprint 29 — Planting Cycle History

**Outcome:** Preserve durable planting-cycle history when a pod is reset so prior crops are not lost when the pod is reused.

**Acceptance criteria:**
- Resetting a non-empty pod records one completed planting-cycle snapshot before clearing the pod.
- Completed cycles preserve plant name, planted date, final status, and end timestamp.
- Resetting an already empty pod does not create empty/junk history rows.
- Existing notes and photos remain unchanged by reset.
- The pod side panel displays recent completed planting cycles.
- Planting-cycle records are read-only in Django admin.
- Pod API responses expose planting-cycle history read-only.
- API clients cannot create or mutate planting-cycle history through pod writes.
- Complete ZIP backups include planting-cycle history and restore it on import.
- Legacy JSON export/import remains unchanged.
- Regression tests cover active reset history, empty reset behavior, UI rendering, API read-only behavior, and ZIP backup/import preservation.
- A schema migration, README, and sprint documentation are included.

**Branch:** `feature/planting-cycle-history`

**Status:** Complete — merged in PR #49.


### Sprint 30 — Garden Activity Timeline

**Outcome:** Surface garden history in one chronological view so users can quickly review plantings, pod notes, photo notes, and completed planting cycles without opening each pod individually.

**Acceptance criteria:**
- Garden detail shows a newest-first activity timeline built from existing data.
- Current planted dates appear as planting events.
- Pod notes appear as note events.
- Notes with photos are visibly identified without exposing private photo contents in the timeline.
- Completed planting cycles appear as completion events with plant name and final status.
- Timeline can be filtered by event type.
- Timeline can be filtered by pod position.
- Invalid filter values fall back safely to the unfiltered timeline.
- Timeline is capped to the 50 newest matching events.
- Existing garden ownership/guest access controls continue to scope all timeline data.
- No new database table is required; timeline remains a derived read-only view.
- Regression tests cover combined events, ordering, event-type filtering, pod filtering, and invalid-filter fallback.
- README and sprint documentation are updated.

**Branch:** `feature/garden-activity-timeline`

**Status:** Complete — merged in PR #50.


### Sprint 31 — Pod Care Reminders

**Outcome:** Add lightweight future-care tracking so growers can record upcoming pod tasks and quickly see what is due or overdue.

**Acceptance criteria:**
- Pod-scoped reminders include a title, due date, creation timestamp, and optional completion timestamp.
- Owners and browser-scoped guest gardens can add reminders using existing garden access controls.
- Reminders can be completed, reopened, and deleted from the pod side panel.
- Overdue reminders are clearly highlighted.
- Garden detail shows the next open reminders across pods and an overdue count.
- My Gardens summaries show open and overdue reminder counts.
- Completed reminders appear in the filterable garden activity timeline.
- Public garden snapshots do not expose private reminder contents.
- Pod API responses expose reminders read-only; nested pod writes cannot create or mutate reminder records.
- Complete ZIP backups include reminder state and restore it on import.
- Legacy JSON export/import remains unchanged.
- Django admin supports reminder review.
- Regression tests cover reminder lifecycle, ownership, dashboard visibility, public privacy, API read-only behavior, and ZIP backup/import preservation.
- A schema migration, README, and sprint documentation are included.

**Branch:** `feature/pod-care-reminders`

**Status:** In review.
