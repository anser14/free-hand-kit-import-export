"""Post-commit lifecycle hooks for host application integrations."""

from __future__ import annotations

import logging
from uuid import UUID

from django.dispatch import Signal

from .models import ImportJob

logger = logging.getLogger(__name__)

import_job_previewed = Signal()
"""Sent after a preview has committed with the job ID, resource key, and submitter ID."""

import_job_queued = Signal()
"""Sent after a confirmed import has been queued for processing."""

import_job_committed = Signal()
"""Sent after a worker has atomically committed host records and the terminal job state."""

import_job_failed = Signal()
"""Sent after a preview or worker has committed a terminal failed job state."""


_SIGNALS_BY_STATUS: dict[str, Signal] = {
    ImportJob.Status.PREVIEWED: import_job_previewed,
    ImportJob.Status.QUEUED: import_job_queued,
    ImportJob.Status.COMMITTED: import_job_committed,
    ImportJob.Status.FAILED: import_job_failed,
}


def send_lifecycle_signal(
    *,
    previous_status: str,
    job_id: UUID,
    resource_key: str,
    submitted_by_id: object,
    status: str,
) -> None:
    """Deliver the terminal or user-visible transition without breaking import processing.

    Callers invoke this function through ``transaction.on_commit``. A receiver failure
    is logged but cannot retroactively fail a committed import or turn a successful API
    response into an error.
    """

    if status == previous_status:
        return
    signal = _SIGNALS_BY_STATUS.get(status)
    if signal is None:
        return
    for receiver, response in signal.send_robust(
        sender=ImportJob,
        job_id=job_id,
        resource_key=resource_key,
        submitted_by_id=submitted_by_id,
    ):
        if isinstance(response, BaseException):
            receiver_name = getattr(receiver, "__qualname__", repr(receiver))
            logger.error(
                "Freehand Kit import lifecycle receiver failed: %s",
                receiver_name,
                exc_info=(type(response), response, response.__traceback__),
            )
