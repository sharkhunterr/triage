from triage.adapters.types import EmailMessage, ServiceCheck, ServiceError


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []
        self.down = False

    async def check(self) -> ServiceCheck:
        return ServiceCheck(not self.down, "connected to smtp.test")

    async def send(self, message: EmailMessage) -> None:
        if self.down:
            raise ServiceError("Email", "SMTPConnectError: refused")
        self.sent.append(message)
