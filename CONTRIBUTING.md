# Contributing to Smart Garden

Thank you for improving Smart Garden.

Before making changes, read:

- [Sprint process](docs/SPRINTS.md)
- [Coding standards](docs/CODING_STANDARDS.md)
- [Development workflow](docs/DEVELOPMENT_WORKFLOW.md)

## Minimum contribution requirements

1. Branch from the latest `main`.
2. Keep the change focused.
3. Add or update tests for behavior changes.
4. Run:

   ```bash
   python manage.py check
   python manage.py test --verbosity=2
   ```

5. Update relevant documentation.
6. Open a PR with a clear summary and testing notes.
7. Resolve CI failures before merge.

Do not commit credentials, secrets, production data, or generated local environment files.
