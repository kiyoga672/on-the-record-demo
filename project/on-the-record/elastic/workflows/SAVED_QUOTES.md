# Saved quotations and reminders

`saved.py` registers `saved_quotes`, the native `save_quote` Workflow, the
`save_quote` Agent Builder tool and the native `reminder_digest` Workflow. Existing
agent tool IDs and existing saved documents are preserved. Inputs are declared in
the manual trigger for the verified 9.5.5 deployment. Compatibility with 9.4 is not
claimed.

Saving requires a server-created ownership marker and management capability hash.
The Workflow repeats the ownership check and exact source check against Hansard,
including speaker, speech ID, date, chamber and URL. Name and party are taken from
the fresh source record. A scripted upsert makes duplicate saves no-ops, preserving
the original creation and delivery state. The HTTP API must confirm that the saved
document exists after a successful execution; a skipped verification is not a save.

`reminder_digest.yaml` contains the complete deterministic native delivery plan:
daily/manual triggers, due-date and monthly guards, recipient aggregation, ownership
lock, fresh selection under the lock, plain-text connector execution, updates only
after connector `status: ok`, and lock release. No LLM is used. Explicit send-now
requires a matching email capability and selects pending quotes regardless of their
future reminder date. A recurring quote is not resent within the same UTC month.
Monthly scheduled delivery uses UTC and runs on the first day of the month.

The Workflow is **disabled**. `EMAIL_CONNECTOR_ID` is not configured and email
delivery has not been authorized or tested. Registration never enables delivery,
even if a connector is later configured. A missing connector and disabled delivery
must be reported to the user rather than presented as a sent message. Before
enabling it, configure a verified email connector, obtain authorization for a test
recipient, validate an actual Workflow execution, and verify the provider and saved
document state. The current native plan processes at most 1,000 recipient groups
and 1,000 pending quotes per recipient per execution; larger deployments need
pagination. A pending claim following an ambiguous delivery must be reconciled
with the provider before manual release. Never automatically clear it and retry.

`reminder_worker.py` is an alternative, unscheduled Python implementation and is
not deployed. Default execution is a read-only dry-run with counts only. Its
explicit `--send` flag performs connector delivery. It shares the durable ownership
lock with the native plan and re-reads due state after acquiring it, so concurrent
selections cannot resend stale quotes. Do not schedule both implementations.

Console steps and worker output contain no recipient addresses or email bodies.
Elastic's workflow execution storage may retain step inputs and outputs, including
mail connector payloads. Restrict access to execution history and configure
appropriate platform retention before production use; this implementation cannot
claim that platform execution storage never contains personal data.

Validation performed without sending mail:

- Both native workflows imported with `valid: true`; save is enabled, reminder is disabled.
- Two real save executions stored the same exact quote at one document ID. Only
  isolated `example.invalid` test records were removed afterwards.
- Native due-selection and recipient-aggregation Elasticsearch query executed successfully.
- Six no-network worker tests cover due dates, future-date send-now, monthly
  guards, exact formatting, confirmed-only state updates, ambiguous failures and
  stale-selection concurrency.
- The attempted manual reminder Workflow probe was rejected by automatic approval
  review because even a nonexistent recipient with `send_now` can trigger email.
  No workaround or email delivery was attempted.
