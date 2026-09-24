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
- request quotas/rate limits by plan;
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
6. Add plan-specific quotas/rate limits before broadly marketing the API.
