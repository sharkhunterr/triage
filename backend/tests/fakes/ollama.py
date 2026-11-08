from collections.abc import Awaitable, Callable

from triage.adapters.types import AiVerdict, ServiceCheck, ServiceError


class FakeOllama:
    """Scripted AI: ``answer`` is returned; ``error`` simulates a timeout or a bad answer."""

    def __init__(self, answer: AiVerdict | None = None) -> None:
        self.answer = answer or AiVerdict(category="unsure", confidence=0.0, reasoning="no idea")
        self.error: ServiceError | None = None
        self.prompts: list[tuple[str, str, list[str]]] = []
        self.during: Callable[[], Awaitable[None]] | None = None  # runs while "thinking"

    async def check(self) -> ServiceCheck:
        return ServiceCheck(self.error is None, "2 models" if self.error is None else self.error.message)

    async def models(self) -> list[str]:
        return ["mistral:7b", "qwen3:8b"]

    async def classify(self, system: str, user: str, category_keys: list[str]) -> AiVerdict:
        self.prompts.append((system, user, category_keys))
        if self.during is not None:
            await self.during()
        if self.error is not None:
            raise self.error
        return self.answer
