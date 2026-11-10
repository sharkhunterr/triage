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


ATTEMPT = 4  # seconds an address gets before the next one is tried


def _interleaved(infos: list[tuple]) -> list[tuple]:  # type: ignore[type-arg]
    """IPv6 and IPv4 addresses taken in turn (RFC 8305), so a broken family is not tried twice in a row."""
    v6 = [i for i in infos if i[0] == socket.AF_INET6]
    v4 = [i for i in infos if i[0] != socket.AF_INET6]
    mixed = [i for pair in zip(v6, v4, strict=False) for i in pair]
    return mixed + v6[len(v4) :] + v4[len(v6) :]


async def _connected_socket(host: str, port: int) -> socket.socket:
    """A TCP connection to the first of the host's addresses that answers. An address that stalls — a
    half-working IPv6 route is common at home — costs a few seconds, not the whole timeout. Plain socket
    calls: uvloop, the server's loop, has no happy eyeballs option."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + TIMEOUT
    infos = await asyncio.wait_for(loop.getaddrinfo(host, port, type=socket.SOCK_STREAM), TIMEOUT)
    addresses = _interleaved(infos)
    error: Exception = TimeoutError()
    for n, (family, kind, proto, _, address) in enumerate(addresses):
        left = deadline - loop.time()
        if left <= 0:
            break
        sock = socket.socket(family, kind, proto)
        sock.setblocking(False)
        try:
            last = n == len(addresses) - 1
            await asyncio.wait_for(loop.sock_connect(sock, address), left if last else min(ATTEMPT, left))
            return sock
        except (OSError, TimeoutError) as exc:
            sock.close()
            error = exc
    raise error


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
        except OSError as exc:
            raise aiosmtplib.SMTPConnectError(
                f"Error connecting to {self._host} on port {self._port}: {exc}"
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
