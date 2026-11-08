from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from triage.adapters.factory import AdapterFactory
from triage.core.config import RuntimeConfig
from triage.core.security import LoginThrottle
from triage.worker.runner import Worker


@dataclass
class AppState:
    config: RuntimeConfig
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    adapter_factory: AdapterFactory
    worker: Worker
    http: httpx.AsyncClient
    throttle: LoginThrottle
