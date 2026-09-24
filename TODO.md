# TODO — Smart Garden next tasks

This file captures follow-up ideas and work items from the recent refactors, accessibility fixes, registration flow, and test additions.

2. ✅ Add HTML email templates and plain-text fallbacks
   - Added confirmation and welcome templates in both HTML and plain text.
   - Registration and welcome messages now use `EmailMultiAlternatives` with regression coverage for both MIME parts.

3. ✅ Add transactional email provider examples and config notes
   - Added environment-backed Django email settings and a production SMTP example.
   - Documented generic SMTP plus SendGrid, Mailgun, and Amazon SES SMTP configuration.

4. ✅ Scaffold Celery for async email sending
   - Added the Celery application and reusable templated-email task with worker documentation.
   - Email dispatch remains synchronous unless `CELERY_BROKER_URL` is configured, preserving simple/local deployments.

5. ✅ Expanded tests for guest flows and import/export edge cases
   - Covered `guest_start` cookie creation/reuse, guest sharing restrictions, true export→import roundtrip behavior, missing-field defaults, and navbar guest badge visibility.
   - Import view now reuses its parsing/validation/creation helpers so the tested path and helper behavior stay aligned.

6. ✅ Investigate "Session data corrupted" warnings
   - Root cause: development generated a new `SECRET_KEY` on every startup, invalidating Django's signed database-session payloads after restarts.
   - Development now uses a stable development-only key; production requires an explicit `SECRET_KEY`, with recovery guidance documented.

7. ✅ Re-run full test suite and fix failures/warnings
   - Latest main CI passes the full Django suite; the prior session warning is resolved.
   - CI now supplies an explicit test `SECRET_KEY`, creates `staticfiles/` before Django initializes WhiteNoise, and runs `manage.py check` before migrations/tests.

8. ✅ Commit and push changes with clear message
   - Follow-up work is being delivered through focused feature/fix branches and reviewed pull requests.

---

If you want, I can pick one of these and implement it now (README update, email templates, Celery scaffold, or tests).