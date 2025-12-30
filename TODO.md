# TODO — Smart Garden next tasks

This file captures follow-up ideas and work items from the recent refactors, accessibility fixes, registration flow, and test additions.

2. Add HTML email templates and plain-text fallbacks
   - Create `templates/emails/confirm_registration.html` and `confirm_registration.txt` (and welcome templates).
   - Use `EmailMultiAlternatives` in views/tasks to send HTML+plain alternatives.

3. Add transactional email provider examples and config notes
   - Include example env variables for SendGrid, Mailgun, SES, and SMTP.
   - Provide minimal Django `EMAIL_BACKEND` examples in README.

4. Scaffold Celery for async email sending
   - Add `celery.py`, a `tasks.send_confirmation_email` task, and docs for running a worker.
   - Keep it optional (only used when `CELERY_BROKER_URL` present).

5. Add / expand tests for guest flows and import/export edge cases
   - Tests: `guest_start` creation and cookie behavior; guest cannot toggle public; import/export roundtrip with missing fields; navbar guest badge visibility.

6. Investigate "Session data corrupted" warnings
   - Reproduce locally and in tests; inspect `SESSION_ENGINE` and cookie signing.
   - Add guidance or fix (clear corrupted sessions in dev, rotate keys before prod use).

7. Re-run full test suite and fix failures/warnings
   - Execute `python3 manage.py test --verbosity=2` and resolve any failures or warnings observed (session warnings, template warnings).

8. Commit and push changes with clear message
   - Commit all changes in a focused commit and push to a new branch (e.g., `feature/registration-accessibility`).

---

If you want, I can pick one of these and implement it now (README update, email templates, Celery scaffold, or tests).