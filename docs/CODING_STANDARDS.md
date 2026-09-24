# Coding Standards

These standards apply to Smart Garden application code, tests, templates, configuration, and automation.

## General principles

- Prefer clear, maintainable code over clever abstractions.
- Keep functions and views focused on one responsibility.
- Reuse existing helpers and constants instead of duplicating logic.
- Preserve backwards compatibility unless a breaking change is intentional and documented.
- Never commit secrets, tokens, credentials, private keys, or production data.
- Treat warnings as useful signals; investigate new warnings rather than normalizing them.

## Python and Django

- Follow PEP 8 conventions and idiomatic Django patterns.
- Use type hints for reusable helpers and non-trivial functions where they improve clarity.
- Use descriptive names; avoid ambiguous single-letter names outside tiny local loops.
- Prefer Django ORM and framework facilities over hand-written equivalents.
- Use `get_object_or_404` or explicit ownership filters for object access.
- Enforce authorization server-side. UI visibility is not an authorization boundary.
- Restrict state-changing endpoints to appropriate HTTP methods.
- Use Django forms/model validation rather than duplicating validation in templates.
- Keep environment-specific values in settings/environment variables.

## Views and business logic

- Keep reusable parsing/validation/business logic in helpers or service/task modules rather than duplicating it across views.
- Return 404/403-style behavior consistently for unauthorized object access according to the existing application pattern.
- Destructive operations must require an explicit state-changing request and should have a confirmation UI.
- Background execution must have a safe synchronous or local-development path when the feature is documented as optional.

## Models and migrations

- Every schema change requires a migration.
- Migrations must be deterministic and safe to apply to existing data.
- Avoid destructive migrations without an explicit migration/backup plan.
- Model relationships and cascade behavior should be tested when deletion semantics matter.

## Templates and frontend

- Keep templates semantic and accessible.
- Forms must include CSRF protection.
- Controls should have clear labels and accessible names.
- Prefer Bootstrap/HTMX conventions already used by the project.
- Keep page-specific CSS in the appropriate static stylesheet rather than growing large inline style blocks.
- User-facing success/error messages should use the shared Django messages rendering.

## Security

- Never trust client-side ownership or identifiers.
- Validate uploaded/imported data before persistence.
- Keep `SECRET_KEY`, SMTP credentials, database passwords, and broker URLs outside source control.
- Production must fail safely when required secrets are missing.
- Public-share functionality must not expose private owner-only actions.
- New API endpoints require explicit authentication/permission review.

## Tests

Behavior changes require tests.

At minimum, test:

- the successful path;
- relevant validation failures;
- authentication/authorization boundaries;
- destructive/cascade behavior when applicable;
- regression cases for bugs being fixed.

Tests should be deterministic and independent. Do not depend on execution order or external production services.

Standard verification:

```bash
python manage.py check
python manage.py test --verbosity=2
```

## Documentation

Update documentation in the same PR when changing:

- environment variables;
- local setup;
- Docker behavior;
- API behavior;
- user-facing workflows;
- background workers;
- security/deployment expectations.

## Dependencies

- Prefer maintained dependencies with clear project value.
- Avoid adding a dependency for functionality that is trivial and safer to implement with the standard library/framework.
- Renovate updates should still pass the full CI suite before merge.
- Version constraints should avoid accidental unsupported major-version upgrades.

## Code review checklist

Before considering a PR ready:

- scope is focused;
- no secrets or sensitive data are present;
- authorization is correct;
- tests cover the behavior;
- docs are current;
- CI is green;
- no new unexplained warnings are present;
- local/Docker workflows remain valid when affected.
