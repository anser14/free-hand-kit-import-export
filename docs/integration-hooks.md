# Integration hooks

Host applications can react to import lifecycle changes with standard Django signals.
They are emitted with `sender=ImportJob` only after the database transaction commits, so
receivers never observe a job or imported host rows that later roll back.

```python
from django.dispatch import receiver

from fk_import_export.models import ImportJob
from fk_import_export.signals import import_job_committed


@receiver(import_job_committed, sender=ImportJob)
def notify_import_complete(sender, *, job_id, resource_key, submitted_by_id, **kwargs):
    # Reload only the data your integration needs. Do not expose source_file publicly.
    job = sender.objects.get(id=job_id)
    queue_notification_for_user(submitted_by_id, resource_key, job.summary)
```

The available signals are:

- `import_job_previewed`
- `import_job_queued`
- `import_job_committed`
- `import_job_failed`

Every signal payload includes `job_id`, `resource_key`, and `submitted_by_id`. `job_id`
is a UUID, `resource_key` is the configured public resource key, and `submitted_by_id`
may be `None` if the submitting user was deleted. Reload the job after receiving a
signal instead of relying on an in-memory model instance.

Receivers are called synchronously after commit. Keep them fast and hand off email,
webhooks, or expensive audit work to the host project's job runner. Receiver exceptions
are logged and intentionally isolated: they cannot roll back an already committed import
or change a successful API response. Signals are an integration notification mechanism,
not a guaranteed delivery queue; use an outbox or durable task system when delivery must
be retried or audited.
