"""Email through SMTP (STARTTLS, SSL, or plain on a trusted LAN)."""

import asyncio
import socket
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from email.message import EmailMessage as MimeMessage

import aiosmtplib

from triage.adapters.types import EmailMessage, ServiceCheck, ServiceError

SERVICE = "Email"
TIMEOUT = 20


async def _connected_socket(host: str, port: int) -> socket.socket:
    """A TCP connection raced over the host's IPv6 and IPv4 addresses (RFC 8305): an address that stalls —
    a half-working IPv6 route is common at home — no longer costs the whole timeout."""
    loop = asyncio.get_running_loop()
    transport, _ = await asyncio.wait_for(
        loop.create_connection(asyncio.Protocol, host, port, happy_eyeballs_delay=0.25), TIMEOUT
    )
    try:
        return transport.get_extra_info("socket").dup()  # type: ignore[no-any-return]
    finally:
        transport.abort()


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

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[aiosmtplib.SMTP]:
        try:
            sock = await _connected_socket(self._host, self._port)
        except TimeoutError as exc:
            raise aiosmtplib.SMTPConnectTimeoutError(
                f"Timed out connecting to {self._host} on port {self._port}"
            ) from exc
        smtp = aiosmtplib.SMTP(
            hostname=self._host,
            sock=sock,
            use_tls=self._security == "ssl",
            start_tls=self._security == "starttls",
            timeout=TIMEOUT,
        )
        try:
            async with smtp:
                if self._username:
                    await smtp.login(self._username, self._password)
                yield smtp
        finally:
            sock.close()

    async def check(self) -> ServiceCheck:
        started = time.monotonic()
        try:
            async with self._session():
                pass
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
            async with self._session() as smtp:
                await smtp.send_message(mime)
        except (aiosmtplib.SMTPException, OSError) as exc:
            raise ServiceError(SERVICE, f"{exc.__class__.__name__}: {exc}") from exc
