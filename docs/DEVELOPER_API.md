# Developer API Access and Paywall

Smart Garden exposes Django REST Framework endpoints under `/api/`. These endpoints are suitable for external developer integrations, so the application includes an optional entitlement gate that can sit behind a paid developer plan.

## Current API surface

The API currently exposes:

- `/api/gardens/`
- `/api/pods/`
- `/api/pod-notes/`
- `/api/global-notes/`
- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`
- `/api-token-auth/`

Garden, pod, and pod-note data is owner-scoped. Global notes are publicly readable when the developer paywall is disabled.

## Enabling the paywall

Set:

```ini
API_PAYWALL_ENABLED=True
```

When enabled, DRF API viewsets require an active `DeveloperAccess` entitlement. Staff and superusers bypass the entitlement check for administration and support.

The schema/documentation pages and token-issuing endpoint remain reachable so developers can discover the API and authenticate, but data endpoints reject callers without an active entitlement.

## DeveloperAccess model

Each paid developer account can have one entitlement record with:

- user
- plan: Starter, Pro, or Enterprise
- status: Inactive, Active, Past due, or Canceled
- billing provider
- billing customer ID
- billing subscription ID
- optional access expiration time

Access is granted only when status is `Active` and the optional expiration time has not passed.

Administrators can manage these records in Django admin.

## Plan-based request limits

When `API_PAYWALL_ENABLED=True`, active developer accounts are throttled per user according to their plan. Defaults are:

- Starter: `100/hour`
- Pro: `1000/hour`
- Enterprise: `5000/hour`

Override the defaults through environment variables:

```ini
API_RATE_STARTER=100/hour
API_RATE_PRO=1000/hour
API_RATE_ENTERPRISE=5000/hour
```

Django REST Framework accepts rate strings such as `60/minute`, `1000/hour`, or `10000/day`.

**Production cache:** Set `API_THROTTLE_CACHE_URL=redis://redis:6379/1` and start the Redis service with `docker compose --env-file .env.prod -f docker-compose.prod.yml --profile api-paywall up -d --build`. Redis database 1 keeps throttle keys separate from the optional Celery broker on database 0. Production startup refuses to enable the paywall without a shared cache URL; an in-process cache would give each web worker a separate quota. For a non-Compose deployment, point the URL at a shared Redis instance accessible by every web replica. If Redis is unavailable, API throttling will fail rather than silently falling back to per-process counters. DRF's standard cache throttles are approximate under concurrent requests and are not a hard billing or abuse-protection boundary.

Rate limiting is disabled when the developer paywall is disabled. Staff and superusers bypass plan throttling for administration and support. Throttle counters are per authenticated user and per plan, so changing a user's plan immediately applies that plan's rate bucket.

## Billing-provider integration

The entitlement model deliberately does not depend on a billing vendor. A billing integration should treat the payment provider as the source of billing events and Smart Garden as the source of API authorization.

Recommended flow:

1. Developer creates/signs into a Smart Garden account.
2. Developer selects an API plan.
3. Smart Garden creates a checkout/session with the chosen billing provider.
4. The billing provider completes payment.
5. A signed webhook reaches Smart Garden.
6. The webhook creates or updates `DeveloperAccess`:
   - successful subscription -> `ACTIVE`
   - failed/overdue payment -> `PAST_DUE`
   - cancellation -> `CANCELED`
7. API requests immediately use the updated entitlement.

Do not trust browser redirects as proof of payment. Entitlement changes should be driven by verified server-to-server webhook events.

## Suggested next billing phase

A future billing sprint can add:

- developer-plan pricing configuration;
- hosted checkout;
- billing portal/customer self-service;
- signed webhook processing;
- automatic entitlement synchronization;
- API usage metering;
- developer dashboard for token and subscription status.

The current entitlement layer is the boundary those features plug into, so adding a billing provider later should not require rewriting API permissions.

## Rollout

A safe rollout sequence is:

1. Leave `API_PAYWALL_ENABLED=False` while configuring plans and test accounts.
2. Create `DeveloperAccess` records for approved/test developers.
3. Validate API calls with active, inactive, past-due, and expired accounts.
4. Integrate billing webhooks.
5. Enable `API_PAYWALL_ENABLED=True` in production.
6. Tune `API_RATE_STARTER`, `API_RATE_PRO`, and `API_RATE_ENTERPRISE` to match the commercial plans before broadly marketing the API.
