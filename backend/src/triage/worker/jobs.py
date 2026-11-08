"""Wires the job handlers and hooks into one worker. Each user story adds its jobs here."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from triage.adapters.factory import AdapterFactory
from triage.worker.runner import Handler, Worker


def build_worker(
    session_factory: async_sessionmaker[AsyncSession], adapter_factory: AdapterFactory
) -> Worker:
    handlers: dict[str, Handler] = {}
    return Worker(session_factory, adapter_factory, handlers)
