"""Wires the job handlers and hooks into one worker. Each user story adds its jobs here."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage.adapters.factory import AdapterFactory
from triage.worker.classify import classify_job
from triage.worker.move import move_given_up, move_job
from triage.worker.poller import poll
from triage.worker.runner import Handler, Worker


def build_worker(
    session_factory: async_sessionmaker[AsyncSession], adapter_factory: AdapterFactory
) -> Worker:
    handlers: dict[str, Handler] = {"classify": classify_job, "move": move_job}
    return Worker(session_factory, adapter_factory, handlers, poll=poll, give_up={"move": move_given_up})
