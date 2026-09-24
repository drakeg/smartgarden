# Development Workflow

## Supported local workflow

The preferred containerized development path is:

```bash
docker compose up --build
```

The direct Python workflow remains supported:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py test --verbosity=2
python manage.py runserver
```

## Before starting work

1. Start from the latest `main`.
2. Confirm CI on `main` is green.
3. Review open PRs and issues for overlap.
4. Create a focused branch using the conventions in `docs/SPRINTS.md`.

## During implementation

- Keep the change scoped to the sprint outcome.
- Add tests as behavior is added or corrected.
- Keep documentation synchronized with code/configuration.
- Do not bypass authorization or validation just to make UI flows work.
- If a pipeline failure appears, inspect the failing job/log first and fix the root cause on the same branch.

## Local validation

For ordinary Django changes:

```bash
python manage.py check
python manage.py test --verbosity=2
```

For Docker-related changes:

```bash
docker compose config
docker compose up --build
```

Verify the affected user workflow manually when practical.

## Pull requests

PR descriptions should include:

- **Summary** — what changed and why.
- **Testing** — automated and manual verification performed.
- **Risks/notes** — migrations, configuration, compatibility, or deployment implications when relevant.

Keep PRs focused. Unrelated cleanup should generally become a separate PR unless it is required to safely complete the feature.

## CI failures

When CI fails:

1. Inspect the exact failed job and step.
2. Read the traceback/log output.
3. Reproduce locally when practical.
4. Fix the root cause on the existing PR branch.
5. Add/adjust regression coverage.
6. Re-run CI.
7. Do not merge until required checks are green.

## Documentation ownership

The repository documentation is part of the product.

- `README.md` — setup, operation, and high-level feature documentation.
- `docs/SPRINTS.md` — sprint process and sprint history/baseline.
- `docs/CODING_STANDARDS.md` — coding, testing, security, and review standards.
- `docs/DEVELOPMENT_WORKFLOW.md` — day-to-day development and PR workflow.
- `TODO.md` — short-lived backlog/history; completed items should not become the only source of permanent documentation.

## Definition of a healthy main branch

`main` should always have:

- passing required CI;
- no known merge conflicts in active work;
- current setup instructions;
- a working local Docker Compose path;
- tests that represent critical application behavior;
- no known critical security/configuration regressions.
