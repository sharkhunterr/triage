"""Email through SMTP (STARTTLS, SSL, or plain on a trusted LAN)."""

import time
from email.message import EmailMessage as MimeMessage

import aiosmtplib

from triage.adapters.types import EmailMessage, ServiceCheck, ServiceError

SERVICE = "Email"


class SmtpMailer:
    def __init__(
        self, host: str, port: int, security: str, username: str, password: str, sender: str
    ) -> None:
        self._host = host
        self._port = port
        self._security = security
        self._username = username
        self._password = password
        self._sender = sender

    def _client(self) -> aiosmtplib.SMTP:
        return aiosmtplib.SMTP(
            hostname=self._host,
            port=self._port,
            use_tls=self._security == "ssl",
            start_tls=self._security == "starttls",
            timeout=20,
        )

    async def check(self) -> ServiceCheck:
        started = time.monotonic()
        try:
            async with self._client() as smtp:
                if self._username:
                    await smtp.login(self._username, self._password)
        except (aiosmtplib.SMTPException, OSError) as exc:
            return ServiceCheck(
                False, f"{exc.__class__.__name__}: {exc}", int((time.monotonic() - started) * 1000)
            )
        return ServiceCheck(True, f"connected to {self._host}", int((time.monotonic() - started) * 1000))

    async def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()
        mime["From"] = self._sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        for key, value in message.headers.items():
            mime[key] = value
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")
        try:
            async with self._client() as smtp:
                if self._username:
                    await smtp.login(self._username, self._password)
                await smtp.send_message(mime)
        except (aiosmtplib.SMTPException, OSError) as exc:
            raise ServiceError(SERVICE, f"{exc.__class__.__name__}: {exc}") from exc
