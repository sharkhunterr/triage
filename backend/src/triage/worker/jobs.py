"""Wires the job handlers and hooks into one worker. Each user story adds its jobs here."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage.adapters.factory import AdapterFactory
from triage.worker.classify import classify_job
from triage.worker.email import notify_held, send_email_job
from triage.worker.move import move_given_up, move_job
from triage.worker.poller import poll
from triage.worker.runner import Handler, Worker
from triage.worker.scan import scan_movie_job, scan_start_job
from triage.worker.verify_request import verify_request_job


def build_worker(
    session_factory: async_sessionmaker[AsyncSession], adapter_factory: AdapterFactory
) -> Worker:
    handlers: dict[str, Handler] = {
        "classify": classify_job,
        "move": move_job,
        "send_email": send_email_job,
        "scan_start": scan_start_job,
        "scan_movie": scan_movie_job,
        "verify_request": verify_request_job,
    }
    return Worker(
        session_factory,
        adapter_factory,
        handlers,
        poll=poll,
        after_drain=notify_held,
        give_up={"move": move_given_up},
    )
