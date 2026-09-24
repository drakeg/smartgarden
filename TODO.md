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

6. Investigate "Session data corrupted" warnings
   - Reproduce locally and in tests; inspect `SESSION_ENGINE` and cookie signing.
   - Add guidance or fix (clear corrupted sessions in dev, rotate keys before prod use).

7. Re-run full test suite and fix failures/warnings
   - Execute `python3 manage.py test --verbosity=2` and resolve any failures or warnings observed (session warnings, template warnings).

8. Commit and push changes with clear message
   - Commit all changes in a focused commit and push to a new branch (e.g., `feature/registration-accessibility`).

---

If you want, I can pick one of these and implement it now (README update, email templates, Celery scaffold, or tests).