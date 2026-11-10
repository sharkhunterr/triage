import asyncio
import socket

import pytest
import uvloop

from triage.adapters import smtp
from triage.adapters.smtp import SmtpMailer, _connected_socket, _interleaved


def info(family: socket.AddressFamily, host: str) -> tuple:  # type: ignore[type-arg]
    return (family, socket.SOCK_STREAM, 6, "", (host, 25))


def test_addresses_alternate_between_ipv6_and_ipv4():
    v6a, v6b = info(socket.AF_INET6, "::1"), info(socket.AF_INET6, "::2")
    v4 = info(socket.AF_INET, "127.0.0.1")
    assert _interleaved([v6a, v6b, v4]) == [v6a, v4, v6b]


def test_connects_on_uvloop_the_server_loop():
    """The server runs on uvloop: the connection must not lean on asyncio-only options."""

    async def main() -> None:
        server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            sock = await _connected_socket("localhost", port)  # ::1 refuses, 127.0.0.1 answers
            assert sock.getpeername()[1] == port
            sock.close()

    uvloop.run(main())


def test_a_stalled_address_costs_one_attempt_not_the_whole_timeout(monkeypatch: pytest.MonkeyPatch):
    stalled, good = info(socket.AF_INET6, "2001:db8::1"), info(socket.AF_INET, "127.0.0.1")

    async def main() -> None:
        server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        loop = asyncio.get_running_loop()

        async def resolve(*_: object, **__: object) -> list[tuple]:  # type: ignore[type-arg]
            return [stalled, (*good[:4], ("127.0.0.1", port))]

        connect = loop.sock_connect

        async def sock_connect(sock: socket.socket, address: tuple) -> None:  # type: ignore[type-arg]
            if address[0] == "2001:db8::1":
                await asyncio.sleep(60)
            await connect(sock, address)

        monkeypatch.setattr(loop, "getaddrinfo", resolve)
        monkeypatch.setattr(loop, "sock_connect", sock_connect)
        monkeypatch.setattr(smtp, "ATTEMPT", 0.2)
        async with server:
            started = loop.time()
            sock = await _connected_socket("mail.test", port)
            assert loop.time() - started < 2
            sock.close()

    asyncio.run(main())


def test_an_unreachable_server_is_a_failed_check_not_an_error():
    async def main() -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.close()  # nothing listens there any more
        check = await SmtpMailer("127.0.0.1", port, "none", "", "", "x@test").check()
        assert not check.ok and "SMTPConnectError" in check.detail

    uvloop.run(main())
